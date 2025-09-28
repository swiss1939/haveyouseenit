# tracker/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Used for account recovery and communication.')
    first_name = forms.CharField(max_length=50, required=True, label='First Name')
    last_name = forms.CharField(max_length=50, required=True, label='Last Name')

    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Date of Birth'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['password', 'password2']:
                current_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = current_classes + ' form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already in use. Please use a different one.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        # 1. Let the parent form create the User.
        # This will trigger the signal in signals.py, which creates the empty Profile.
        user = super().save(commit=True)

        # 2. Update the User and the newly created Profile with our form data.
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        
        # The signal guarantees user.profile exists at this point.
        user.profile.date_of_birth = self.cleaned_data["date_of_birth"]

        # 3. Save the updated fields.
        if commit:
            user.save()
            user.profile.save()
        
        return user