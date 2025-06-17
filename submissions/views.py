from django.shortcuts import render, redirect
from .forms import FieldSubmissionForm
from .models import FieldSubmission
from django.db.models import Q

def submit_field_view(request):
    if request.method == 'POST':
        form = FieldSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                submission = form.save(commit=False)
                submission.save()
                return redirect('submissions:success')
            except Exception as e:
                print(f"Error saving submission: {e}")
                form.add_error(None, f"Terjadi kesalahan saat menyimpan data: {e}")
        # Jika form tidak valid, tampilkan error
        print("\n==== DEBUG SUBMIT FIELD ====")
        print("POST:", dict(request.POST))
        print("FILES:", dict(request.FILES))
        print("FORM ERRORS:", form.errors)
        print("NON FIELD ERRORS:", form.non_field_errors())
        print("===========================\n")
    else:
        form = FieldSubmissionForm()
    return render(request, 'submissions/submit_field.html', {'form': form})


# def field_submission_list(request): (DIHAPUS)
    city = request.GET.get('city', '')
    category = request.GET.get('category', '')
    qs = FieldSubmission.objects.all()
    if city:
        qs = qs.filter(city__iexact=city)
    if category:
        qs = qs.filter(category=category)
    # Dapatkan list kota unik dan kategori
    cities = FieldSubmission.objects.exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct()
    categories = FieldSubmission.FIELD_CATEGORIES
    return render(request, 'submissions/field_submission_list.html', {
        'fields': qs,
        'cities': cities,
        'categories': categories,
        'city': city,
        'category': category,
    })
