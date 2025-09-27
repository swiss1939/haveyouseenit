# tracker/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    # Fields for the built-in User model
    email = forms.EmailField(required=True, help_text='Required. Used for account recovery and communication.')
    first_name = forms.CharField(max_length=50, required=True, label='First Name')
    last_name = forms.CharField(max_length=50, required=True, label='Last Name')

    # Field for the custom Profile model
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), # <-- Applied class here
        label='Date of Birth'
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name',) 

    # --- NEW: Constructor to apply 'form-control' class to remaining fields ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply form-control class to all standard fields for Bootstrap styling
        for field_name, field in self.fields.items():
            # Exclude Password fields (handled separately by UserCreationForm)
            if field_name not in ['password', 'password2']: 
                # Add 'form-control' class to the widget's attrs
                current_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = current_classes + ' form-control'
    # --------------------------------------------------------------------------

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("This email address is already in use. Please use a different one.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Assign names and email to the User object
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        
        if commit:
            user.save()

        # Create and save the related Profile model
        Profile.objects.create(
            user=user,
            date_of_birth=self.cleaned_data["date_of_birth"],
        )
        return user
