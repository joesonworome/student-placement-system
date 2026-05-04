from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Student


class SignupForm(UserCreationForm):
    """Same as UserCreationForm but without help_text under fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""
        self.fields["username"].label = "Username"
        self.fields["password1"].help_text = ""
        self.fields["password1"].label = "Password"
        self.fields["password2"].help_text = ""
        self.fields["password2"].label = "Confirm password"


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'student_id', 'email', 'course', 'id_photo']