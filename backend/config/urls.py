from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts import views as accounts
from ai import views as ai
from cart import views as cart
from catalog import views as catalog
from custom_requests import views as custom_requests
from orders import views as orders
from payments import views as payments
from reviews import views as reviews

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
    path("search/", catalog.search),
    path("stores/", catalog.StoreList.as_view()),
    path("stores/<slug:slug>/", catalog.StoreDetail.as_view()),
    path("stores/<slug:slug>/reviews/", catalog.store_reviews),
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
    path("seller/overview/", orders.overview),
    path("seller/store/", catalog.my_store),
    path("seller/store/cover/", catalog.my_store_cover),
    path("seller/products/", catalog.MyProductList.as_view()),
    path("seller/products/<int:pk>/", catalog.MyProductDetail.as_view()),
    path("seller/products/<int:pk>/images/", catalog.product_images),
    path("seller/products/<int:pk>/images/order/", catalog.product_images_order),
    path("seller/products/<int:pk>/images/<int:image_id>/", catalog.product_image_delete),
    path("seller/orders/", orders.IncomingOrderList.as_view()),
    path("seller/orders/<int:pk>/status/", orders.change_status),
    path("seller/reviews/", reviews.my_reviews),
    path("seller/ai/listing/", ai.listing),
    path("seller/requests/", custom_requests.shop_requests),
    path("seller/requests/<int:pk>/quote/", custom_requests.send_quote),
    path("seller/requests/<int:pk>/decline/", custom_requests.seller_decline),
    # reviews (buyer, after delivery)
    path("reviews/", reviews.write),
    # custom requests (buyer)
    path("requests/", custom_requests.my_requests),
    path("requests/<int:pk>/", custom_requests.my_request),
    path("requests/<int:pk>/images/", custom_requests.request_images),
    path("requests/<int:pk>/accept/", custom_requests.accept),
    path("requests/<int:pk>/decline/", custom_requests.decline),
    path("requests/<int:pk>/add-to-bag/", custom_requests.add_to_bag),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
