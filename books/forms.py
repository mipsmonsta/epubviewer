from django import forms
from .models import Book

class BookUploadForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.epub',
                'id': 'epub-file'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            if not file.name.lower().endswith('.epub'):
                raise forms.ValidationError('Please upload an EPUB file.')
            
            # Check file size (limit to 50MB)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 50MB.')
        
        return file
