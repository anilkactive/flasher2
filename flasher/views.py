from django.shortcuts import render
from store.models import Product
from django.http import HttpResponse,HttpRequest

def home (request):
    products = Product.objects.all().filter(is_available=True)
    print(101)
    print(request.user)
    print(102)
    context = {
        'products': products
    }
    return render (request, 'home.html', context)
