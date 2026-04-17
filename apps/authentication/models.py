from django.db import models


class Student(models.Model):
    # ---------------------------
    # BASIC INFORMATION
    # ---------------------------
    full_name = models.CharField(max_length=200)
    student_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)

    # ---------------------------
    # PHOTO (ID / PROFILE)
    # ---------------------------
    id_photo = models.ImageField(
        upload_to='student_photos/',
        blank=True,
        null=True
    )

    # ---------------------------
    # TIMESTAMPS (GOOD PRACTICE)
    # ---------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------------------------
    # STRING REPRESENTATION
    # ---------------------------
    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

    # ---------------------------
    # META OPTIONS (OPTIONAL)
    # ---------------------------
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Student"
        verbose_name_plural = "Students"