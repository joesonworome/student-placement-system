from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# NEW imports for student
from .models import Student
from .forms import StudentForm, SignupForm


# -------------------------------
# REGISTER
# -------------------------------
def register(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'registration/register.html', {'form': form})


# -------------------------------
# REDIRECT
# -------------------------------
def dashboard_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


# -------------------------------
# ADD STUDENT (FIXED)
# -------------------------------
@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully!')
            return redirect('student_list')
    else:
        form = StudentForm()

    return render(request, 'add_student.html', {'form': form})


# -------------------------------
# STUDENT LIST (FIXED)
# -------------------------------
@login_required
def student_list(request):
    students = Student.objects.all()
    return render(request, 'student_list.html', {'students': students})