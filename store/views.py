from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from .models import Product, ProductGallery, VidItem
from category.models import Category
from carts.views import _cart_id
from carts.models import CartItem
# from django.http import HttpResponse

# Create your views here.
# from store.models import Product

def store (request, category_slug=None):
    categories = None
    products = None

    if category_slug != None:
        categories = get_object_or_404(Category, slug = category_slug)
        products = Product.objects.filter(category = categories, is_available=True)
        product_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True)
        product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render (request, 'store/store.html', context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug = category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
        # return HttpResponse(in_cart)
        # exit()
    except Exception as e:
        raise e

    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)
    vidItem = VidItem.objects.filter(product_id=single_product.id)

    context = {
        'single_product': single_product,
        'in_cart'       : in_cart,
        # 'orderproduct': orderproduct,
        'product_gallery': product_gallery,
        'vidItem': vidItem,
    }
    return render (request, 'store/product_detail.html',context)
