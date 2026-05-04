import csv
import io
import os
from datetime import datetime

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from apps.data_uploads.training_data import load_user_student_dataframe

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    letter = None
    canvas = None


# ================================
# MAIN REPORT PAGE
# ================================
@login_required
def generate_report(request):
    df, err = load_user_student_dataframe(request.user)
    if err == "no_dataset":
        messages.error(request, "No data found. Please upload a dataset under Upload Data first.")
        return redirect("upload_data")
    if err:
        messages.error(request, f"Could not read dataset: {err}")
        return redirect("upload_data")
    if df is None:
        messages.error(request, "No data found. Please upload a dataset first.")
        return redirect("upload_data")

    # ================================
    # HANDLE POST (GENERATE REPORT)
    # ================================
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'placement_summary')
        format_type = request.POST.get('format', 'csv')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')

        # Filter by date if available
        if date_from and date_to and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df[(df['date'] >= date_from) & (df['date'] <= date_to)]

        # Generate report
        if report_type == 'placement_summary':
            return generate_summary_report(df, format_type)
        elif report_type == 'student_details':
            return generate_student_report(df, format_type)
        elif report_type == 'model_performance':
            return generate_performance_report(format_type, request)

    # ================================
    # GET REQUEST (SHOW PAGE)
    # ================================
    context = {
        'data_info': {
            'total_students': len(df),
            'has_placement': 'placement_status' in df.columns,
            'columns': df.columns.tolist()
        }
    }

    return render(request, 'reports/generate.html', context)


def _create_pdf_response(filename, lines):
    if letter is None or canvas is None:
        return None

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont('Helvetica-Bold', 18)
    c.drawString(50, height - 50, filename.replace('_', ' ').replace('.pdf', '').title())
    y = height - 80
    c.setFont('Helvetica', 10)

    for line in lines:
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont('Helvetica', 10)
        c.drawString(50, y, line)
        y -= 16

    c.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ================================
# SUMMARY REPORT
# ================================
def generate_summary_report(df, format_type):
    total_students = len(df)

    placed_students = 0
    placement_rate = "N/A"

    if 'placement_status' in df.columns and total_students > 0:
        placed_students = len(df[df['placement_status'] == 1])
        placement_rate = f"{(placed_students / total_students * 100):.2f}%"

    summary = {
        'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Total Students': total_students,
        'Placed Students': placed_students,
        'Placement Rate': placement_rate
    }

    if 'cgpa' in df.columns and total_students > 0:
        summary['Average CGPA'] = f"{df['cgpa'].mean():.2f}"
        summary['Max CGPA'] = f"{df['cgpa'].max():.2f}"
        summary['Min CGPA'] = f"{df['cgpa'].min():.2f}"

    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])

        for key, value in summary.items():
            writer.writerow([key, value])

        return response

    if format_type in ['xlsx', 'excel']:
        output = io.BytesIO()
        summary_df = pd.DataFrame(list(summary.items()), columns=['Metric', 'Value'])
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_df.to_excel(writer, index=False, sheet_name='Summary')
        output.seek(0)

        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response

    if format_type == 'pdf':
        lines = [f"{key}: {value}" for key, value in summary.items()]
        pdf_response = _create_pdf_response(f'summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf', lines)
        if pdf_response is None:
            return HttpResponse('PDF generation dependency not installed. Please install reportlab.', status=500)
        return pdf_response

    return HttpResponse("Report generated")


# ================================
# STUDENT REPORT
# ================================
def generate_student_report(df, format_type):
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        df.to_csv(response, index=False)
        return response

    if format_type in ['xlsx', 'excel']:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
        output.seek(0)

        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response

    if format_type == 'pdf':
        lines = [', '.join(df.columns.tolist())]
        for index, row in df.iterrows():
            lines.append(', '.join(str(value) for value in row.tolist()))

        pdf_response = _create_pdf_response(f'students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf', lines)
        if pdf_response is None:
            return HttpResponse('PDF generation dependency not installed. Please install reportlab.', status=500)
        return pdf_response

    return HttpResponse("Student report generated")


# ================================
# MODEL PERFORMANCE
# ================================
def generate_performance_report(format_type, request):
    model_path = os.path.join(settings.MEDIA_ROOT, 'placement_model.pkl')
    training_info = request.session.get('training_info', {})

    if not os.path.exists(model_path):
        return HttpResponse("No trained model found")

    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])

        if training_info:
            writer.writerow(['Algorithm', training_info.get('algorithm', 'N/A')])
            writer.writerow(['Accuracy', training_info.get('metrics', {}).get('accuracy', 'N/A')])
            writer.writerow(['Precision', training_info.get('metrics', {}).get('precision', 'N/A')])
            writer.writerow(['Recall', training_info.get('metrics', {}).get('recall', 'N/A')])
            writer.writerow(['F1 Score', training_info.get('metrics', {}).get('f1_score', 'N/A')])

        return response

    if format_type in ['xlsx', 'excel']:
        output = io.BytesIO()
        perf_data = []
        if training_info:
            perf_data = [
                ['Algorithm', training_info.get('algorithm', 'N/A')],
                ['Accuracy', training_info.get('metrics', {}).get('accuracy', 'N/A')],
                ['Precision', training_info.get('metrics', {}).get('precision', 'N/A')],
                ['Recall', training_info.get('metrics', {}).get('recall', 'N/A')],
                ['F1 Score', training_info.get('metrics', {}).get('f1_score', 'N/A')],
            ]
        perf_df = pd.DataFrame(perf_data, columns=['Metric', 'Value'])
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            perf_df.to_excel(writer, index=False, sheet_name='Performance')
        output.seek(0)

        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response

    if format_type == 'pdf':
        lines = []
        if training_info:
            lines = [f"Algorithm: {training_info.get('algorithm', 'N/A')}",
                     f"Accuracy: {training_info.get('metrics', {}).get('accuracy', 'N/A')}",
                     f"Precision: {training_info.get('metrics', {}).get('precision', 'N/A')}",
                     f"Recall: {training_info.get('metrics', {}).get('recall', 'N/A')}",
                     f"F1 Score: {training_info.get('metrics', {}).get('f1_score', 'N/A')}" ]
        else:
            lines = ['No model training information available.']

        pdf_response = _create_pdf_response(f'performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf', lines)
        if pdf_response is None:
            return HttpResponse('PDF generation dependency not installed. Please install reportlab.', status=500)
        return pdf_response

    if format_type == 'json':
        return JsonResponse(training_info)

    return HttpResponse("Performance report generated")


# ================================
# DOWNLOAD REPORT
# ================================
@login_required
def download_report(request):
    report_type = request.GET.get('type', 'placement_summary')
    format_type = request.GET.get('format', 'csv')

    df, err = load_user_student_dataframe(request.user)
    if err or df is None:
        return HttpResponse("No data found", status=404)

    if report_type == 'placement_summary':
        return generate_summary_report(df, format_type)
    elif report_type == 'student_details':
        return generate_student_report(df, format_type)
    elif report_type == 'model_performance':
        return generate_performance_report(format_type, request)

    return HttpResponse("Invalid report type", status=400)