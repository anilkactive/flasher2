from django.shortcuts import render, redirect
from carts.models import CartItem
from .forms import OrderForm
import datetime
from .models import Order, OrderProduct
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail
from orders.models import Payment, Order
from store.models import Product
from django.core.mail import EmailMessage
from django.template.loader import render_to_string




# Create your views here.
def place_order(request, total=0, quantity=0,):
    current_user = request.user

    # if cart_count <= 0
    cart_items = CartItem.objects.filter(user = current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total)/100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20210305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            # data.save()

            # order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

            # Payment Gateway
            if request.method == 'POST':
                client = razorpay.Client(auth=("rzp_test_gClpZ0RC9QCyw4", "LFZaHcq3MPpICzUD7WSbjJYV"))
                DATA = {
                    "amount": grand_total*100,
                    "currency": "INR",
                    "payment_capture": "1",
                }

                razP_detail = client.order.create(data=DATA)
                print(razP_detail)

                for key, val in razP_detail.items():
                    if key == 'id':
                        data.raz_order_number = val
                        break

                print('x-123---')
                print(data.raz_order_number)
                data.save()

                order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

                context = {
                    'order': order,
                    'cart_items': cart_items,
                    'total': total,
                    'tax': tax,
                    'grand_total': grand_total,
                    'razP_detail': razP_detail,
                }
            return render(request, 'orders/place_order.html', context)
        else:
            return redirect('checkout')



@csrf_exempt
def order_complete(request):
    if (request.method == 'POST'):
        a = request.POST
        razP_payment_id = ""
        razP_order_id = ""
        razP_signature = ''
        data = {}
        for key, val in a.items():
            if key == 'razorpay_payment_id':
                razP_payment_id = val
                data['razorpay_payment_id'] = val
            if key == 'razorpay_order_id':
                razP_order_id = val
                data['razorpay_order_id'] = val
            if key == 'razorpay_signature':
                razP_signature = val
                data['razorpay_signature'] = val
        print(a)
        print('321')
        print(razP_payment_id)
        print(razP_order_id)
        print(razP_signature)
        print(data)
        client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
        check = client.utility.verify_payment_signature(data)
        print('123--')
        print(check)
        if check:
            payment = Payment(
                user = request.user,
                raz_payment_id = razP_payment_id,
                raz_order_id = razP_order_id,
                raz_signature = razP_signature,
                payment_method = "Razorpay",
                amount_paid = 789,
                status = "Completed",
            )
            payment.save()

            order = Order.objects.get(user=request.user, is_ordered=False, raz_order_number=razP_order_id)
            order.payment = payment
            order.is_ordered = True
            order.save()


            # Move the cart items to Order Product table
            cart_items = CartItem.objects.filter(user=request.user)

            for item in cart_items:
                orderproduct = OrderProduct()
                orderproduct.order_id = order.id        #??
                orderproduct.payment = payment
                orderproduct.user_id = request.user.id  #??
                orderproduct.product_id = item.product_id#??
                orderproduct.quantity = item.quantity
                orderproduct.product_price = item.product.price
                orderproduct.ordered = True
                orderproduct.save()

                # Reduce the quantity of the sold products
                product = Product.objects.get(id=item.product_id)
                product.stock -= item.quantity
                product.save()

            # Clear cart
            CartItem.objects.filter(user=request.user).delete()

            # Send order recieved email to customer
            mail_subject = 'Thank you for your order!'
            message = render_to_string('orders/order_recieved_email.html', {
                'user': request.user,
                'order': order,
            })
            to_email = request.user.email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            # send_email.send()

            # Send order number and transaction id back to sendData method via JsonResponse

            ordered_products = OrderProduct.objects.filter(order_id=order.id)
            subtotal = 0
            for i in ordered_products:
                subtotal += i.product_price * i.quantity

            context = {
                'order_number': order.order_number,
                'transID': payment.raz_payment_id,
                'user': request.user,
                'order': order,
                'status': payment.status,
                'ordered_products': ordered_products,
                'subtotal': subtotal,
            }
            # return JsonResponse(data)
            # try:

            return render(request, 'orders/order_complete.html', context)

        else:
            return render(request, 'store/errorpay.html')

# def order_complete(request):
#     # order_number = request.GET.get('order_number')
#     # transID = request.GET.get('payment_id')
#
#     try:
#         order = Order.objects.get(order_number=order_number, is_ordered=True)
#         ordered_products = OrderProduct.objects.filter(order_id=order.id)
#
#         subtotal = 0
#         for i in ordered_products:
#             subtotal += i.product_price * i.quantity
#
#         payment = Payment.objects.get(payment_id=transID)
#
#         context = {
#             'order': order,
#             'ordered_products': ordered_products,
#             'order_number': order.order_number,
#             'transID': payment.payment_id,
#             'payment': payment,
#             'subtotal': subtotal,
#         }
#         # return render(request, 'orders/order_complete.html', context)
#         return render(request, 'store/paidok.html', context)
#     except (Payment.DoesNotExist, Order.DoesNotExist):
#         return redirect('home')
