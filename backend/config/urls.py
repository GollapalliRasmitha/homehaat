from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts import views as accounts
from cart import views as cart
from catalog import views as catalog
from orders import views as orders
from payments import views as payments

api = [
    # accounts
    path("auth/csrf/", accounts.csrf),
    path("auth/signup/", accounts.signup),
    path("auth/signin/", accounts.signin),
    path("auth/signout/", accounts.signout),
    path("auth/me/", accounts.me),
    path("addresses/", accounts.AddressList.as_view()),
    # catalog (public)
    path("categories/", catalog.CategoryList.as_view()),
    path("products/", catalog.ProductList.as_view()),
    path("products/<int:pk>/", catalog.ProductDetail.as_view()),
    # cart
    path("cart/", cart.cart),
    path("cart/items/", cart.add_item),
    path("cart/items/<int:item_id>/", cart.change_item),
    path("cart/preview/", cart.preview),
    path("cart/merge/", cart.merge),
    # checkout, orders, payments
    path("checkout/", orders.checkout),
    path("orders/", orders.MyOrderList.as_view()),
    path("orders/<int:pk>/", orders.MyOrderDetail.as_view()),
    path("payments/verify/", payments.verify),
    path("payments/webhook/", payments.webhook),
    # seller
    path("seller/store/", catalog.my_store),
    path("seller/products/", catalog.MyProductList.as_view()),
    path("seller/products/<int:pk>/", catalog.MyProductDetail.as_view()),
    path("seller/orders/", orders.IncomingOrderList.as_view()),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
