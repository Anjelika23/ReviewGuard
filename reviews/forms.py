from django import forms


class ReviewAnalysisForm(forms.Form):
    movie = forms.CharField(max_length=32)
    user_id = forms.CharField(max_length=64, required=False)
    account_age_days = forms.IntegerField(min_value=0, max_value=36500, initial=3)
    rating = forms.IntegerField(min_value=1, max_value=5)
    review_text = forms.CharField(min_length=3, max_length=5000, widget=forms.Textarea)

    def clean_user_id(self):
        return self.cleaned_data.get("user_id") or "new_user"
