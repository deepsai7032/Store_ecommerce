from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from .models import Product,Category,Purchase,CartItem
from .forms import ProductForm,UpdateQuantityForm,CategoryForm
from django.core.paginator import Paginator
import os,json,io, base64
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

import numpy as np
import pandas as pd
import matplotlib 
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def MAinview(request):
    categories = Category.objects.all()
    selected = request.GET.get("category")

    products = Product.objects.all()
    if selected:
        products = products.filter(category__name=selected)

    paginator = Paginator(products, 12)
    products = paginator.get_page(request.GET.get("page"))

    return render(request, "Mainpage/home.html", {
        "products": products,
        "categories": categories,
        "selected": selected,
    })

def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST,request.FILES)
        print("FILES RECEIVED:", request.FILES)
        print("FORM VALID:", form.is_valid())
        print("FORM ERRORS:", form.errors)
        if form.is_valid():
            obj=form.save()
            print("SAVED IMAGE PATH:",obj.image)
            messages.success(request, "Product added.")
            if request.POST.get("action") == "view_products":
                return redirect("/DBstore/products/view/")
            else:
                return redirect("/DBstore/products/add/")
    else:
        form = ProductForm()
    return render(request, "DBstore/add_product.html", {"form": form})

'''
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        product.delete()
        messages.success(request, f"Removed {product.name}.")
    return redirect("/DBstore/products/view/")'''

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        product.is_trashed = True
        product.trashed_at = timezone.now()
        product.save(update_fields=["is_trashed", "trashed_at"])
        removed_from_carts = CartItem.objects.filter(product=product).count()
        CartItem.objects.filter(product=product).delete()
        if removed_from_carts:
            messages.success(request, f"Moved {product.name} to trash and removed it from {removed_from_carts} cart(s).")
        else:
            messages.success(request, f"Moved {product.name} to trash.")
    return redirect(request.META.get("HTTP_REFERER", "/DBstore/products/view/"))



def update_quantity(request):
    if request.method == "POST":

        def update_one(pid):
            try:
                product = Product.objects.get(id=pid)
            except Product.DoesNotExist:
                return None
            price = request.POST.get(f"price_{pid}")
            quantity = request.POST.get(f"quantity_{pid}")
            category_id = request.POST.get(f"category_{pid}")
            offer_percent = request.POST.get(f"offer_percent_{pid}")
            if price:
                product.price = price
            if quantity:
                product.quantity = quantity
            product.category_id = category_id if category_id else None
            product.offer_percent = int(offer_percent) if offer_percent else 0
            product.save(update_fields=["price", "quantity", "category",'offer_percent'])
            return product

        if request.POST.get("update_all"):
            selected_ids = request.POST.getlist("selected")
            updated_count = sum(1 for pid in selected_ids if update_one(pid))
            if updated_count:
                messages.success(request, f"Updated {updated_count} product(s).")
            else:
                messages.error(request, "Nothing was updated.")

        elif request.POST.get("product_id"):
            pid = request.POST.get("product_id")
            product = update_one(pid)
            if product:
                messages.success(request, f"Updated {product.name}.")

    return redirect(request.META.get("HTTP_REFERER", "/DBstore/products/manage/"))



def manage_products(request, category_id=None):
    all_categories = Category.objects.filter(is_trashed=False)

    if category_id == "other":
        product_list = Product.objects.filter(category__isnull=True,is_trashed=False)
        paginator = Paginator(product_list, 9)
        products = paginator.get_page(request.GET.get("page"))
        return render(request, "DBstore/manage_products.html", {
            "is_other": True,
            "products": products,
            "categories": all_categories,
        })

    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        product_list = selected_category.products.filter(is_trashed=False)
        paginator = Paginator(product_list, 9)
        products = paginator.get_page(request.GET.get("page"))
        return render(request, "DBstore/manage_products.html", {
            "selected_category": selected_category,
            "products": products,
            "categories": all_categories,
        })

    categories = Category.objects.filter(is_trashed=False).prefetch_related("products").all()
    uncategorized_count = Product.objects.filter(category__isnull=True,is_trashed=False).count()
    return render(request, "DBstore/manage_products.html", {
        "categories": categories,
        "uncategorized_count": uncategorized_count,
    })

def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added.")
            return redirect("/DBstore/products/manage/")
    else:
        form = CategoryForm()
    return render(request, "DBstore/add_category.html", {"form": form})

def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        now = timezone.now()
        category.is_trashed = True
        category.trashed_at = now
        category.save(update_fields=["is_trashed", "trashed_at"])
        products_in_category = category.products.filter(is_trashed=False)
        moved = products_in_category.update(is_trashed=True, trashed_at=now)
        CartItem.objects.filter(product__in=products_in_category).delete()
        messages.success(request, f'Moved "{category.name}" and {moved} product(s) to trash.')
    return redirect("/DBstore/products/manage/")


def trash_view(request):
    trashed_products = Product.objects.filter(is_trashed=True).order_by("-trashed_at")
    trashed_categories = Category.objects.filter(is_trashed=True).order_by("-trashed_at")
    return render(request, "DBstore/trash.html", {
        "trashed_products": trashed_products,
        "trashed_categories": trashed_categories,
    })


def restore_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_trashed=True)
    if request.method == "POST":
        product.is_trashed = False
        product.trashed_at = None
        product.save(update_fields=["is_trashed", "trashed_at"])
        messages.success(request, f"Restored {product.name}.")
    return redirect("/DBstore/trash/")


def restore_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, is_trashed=True)
    if request.method == "POST":
        category.is_trashed = False
        category.trashed_at = None
        category.save(update_fields=["is_trashed", "trashed_at"])
        messages.success(request, f'Restored "{category.name}".')
    return redirect("/DBstore/trash/")


def permanently_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_trashed=True)
    if request.method == "POST":
        if product.image:
            image_path = os.path.join(settings.MEDIA_ROOT, product.image.name)
            if os.path.isfile(image_path):
                os.remove(image_path)
        name = product.name
        product.delete()
        messages.success(request, f"Permanently deleted {name}.")
    return redirect("/DBstore/trash/")


def permanently_delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, is_trashed=True)
    if request.method == "POST":
        name = category.name
        for product in category.products.all():
            if product.image:
                image_path = os.path.join(settings.MEDIA_ROOT, product.image.name)
                if os.path.isfile(image_path):
                    os.remove(image_path)
            product.delete()
        category.delete()
        messages.success(request, f'Permanently deleted "{name}" and all its products.')
    return redirect("/DBstore/trash/")






RESTOCK_LEAD_DAYS = 2
SALES_WINDOW_DAYS = 14

# ---- Colors matched to the site's CSS variables ----
BG = "#242923"
TEXT = "#EDEAE0"
MUTED = "#A6AA9E"
GRID = "#3A4038"
CATEGORY_COLORS = ["#C99A3D", "#7C9473", "#98B58C", "#C9683D", "#8B5A3C", "#A6AA9E", "#5C7A52", "#E0B558"]


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def get_category_color_map():
    """One consistent color per category, reused across every chart on the page."""
    names = list(Category.objects.order_by("name").values_list("name", flat=True))
    names.append("Other")
    return {name: CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i, name in enumerate(names)}


def render_item_chart(names, regular_units, regular_prices, offer_units, offer_prices, categories, color_map, title):
    n = len(names)
    fig, ax = plt.subplots(figsize=(max(9, n * 1.2), 4.4))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    x = np.arange(n)
    width = 0.35
    base_colors = [color_map.get(cat, MUTED) for cat in categories]

    bars_regular = ax.bar(x - width / 2, regular_units, width=width, color=base_colors, zorder=3, label="Regular price")
    bars_offer = ax.bar(x + width / 2, offer_units, width=width, color="#E0B558",
                         edgecolor=base_colors, linewidth=2, zorder=3, label="Offer price")

    for bar, units, price in zip(bars_regular, regular_units, regular_prices):
        if units > 0:
            ax.annotate(f"${price:.2f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 4), ha="center",
                        fontsize=8, color=TEXT, fontweight="bold")

    for bar, units, price in zip(bars_offer, offer_units, offer_prices):
        if units > 0:
            ax.annotate(f"${price:.2f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 4), ha="center",
                        fontsize=8, color="#E0B558", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=35, ha="right", color=MUTED, fontsize=9)
    ax.set_ylabel("Units sold", color=MUTED, fontsize=9)
    ax.tick_params(axis="y", colors=MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    max_val = max(max(regular_units, default=0), max(offer_units, default=0), 1)
    ax.set_ylim(0, max_val * 1.25)

    ax.legend(loc="upper right", facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=8)
    ax.set_title(title, color=TEXT, fontsize=11, loc="left")
    return fig_to_base64(fig)


def render_pie_chart(names, values, color_map=None, title=""):
    fig, ax = plt.subplots(figsize=(4.8, 4.8))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    values_arr = np.array(values, dtype=float)
    if values_arr.sum() == 0:
        values_arr = np.array([1.0])
        names = ["No sales yet"]
        colors = [GRID]
    else:
        colors = [color_map.get(n, MUTED) for n in names] if color_map else CATEGORY_COLORS[: len(names)]

    wedges, texts, autotexts = ax.pie(
        values_arr, labels=names,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 0 else "",
        colors=colors, textprops={"color": TEXT, "fontsize": 9},
        wedgeprops={"edgecolor": BG, "linewidth": 2},
    )
    for autotext in autotexts:
        autotext.set_color(BG)
        autotext.set_fontweight("bold")
    ax.axis("equal")
    if title:
        ax.set_title(title, color=TEXT, fontsize=11, loc="left")
    return fig_to_base64(fig)


def _item_breakdown(purchases_qs):
    rows = list(
        purchases_qs.values("product__name", "product__category__name", "unit_price", "original_price")
        .annotate(units=Sum("quantity"))
    )
    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["category"] = df["product__category__name"].fillna("Other")
    df["is_offer"] = df["unit_price"] < df["original_price"]
    grouped = {}
    for _, row in df.iterrows():
        name = row["product__name"]
        if name not in grouped:
            grouped[name] = {
                "category": row["category"],
                "regular_units": 0, "regular_price": 0,
                "offer_units": 0, "offer_price": 0,
            }
        if row["is_offer"]:
            grouped[name]["offer_units"] += row["units"]
            grouped[name]["offer_price"] = float(row["unit_price"])
        else:
            grouped[name]["regular_units"] += row["units"]
            grouped[name]["regular_price"] = float(row["unit_price"])

    names = list(grouped.keys())
    return {
        "names": names,
        "categories": [grouped[n]["category"] for n in names],
        "regular_units": [grouped[n]["regular_units"] for n in names],
        "regular_prices": [grouped[n]["regular_price"] for n in names],
        "offer_units": [grouped[n]["offer_units"] for n in names],
        "offer_prices": [grouped[n]["offer_price"] for n in names],
    }

def _category_revenue(purchases_qs):
    rows = list(
        purchases_qs.values("product__category__name")
        .annotate(revenue=Sum(F("quantity") * F("product__price")))
        .order_by("-revenue")
    )
    if not rows:
        return [], []
    df = pd.DataFrame(rows)
    df["name"] = df["product__category__name"].fillna("Other")
    return df["name"].tolist(), df["revenue"].tolist()


def dashboard(request):
    now = timezone.now()
    color_map = get_category_color_map()

    # Daily 
    since_1 = now - timedelta(days=1)
    daily_data = _item_breakdown(Purchase.objects.filter(purchased_at__gte=since_1))
    daily_chart = (
        render_item_chart(daily_data["names"], daily_data["regular_units"], daily_data["regular_prices"],
                           daily_data["offer_units"], daily_data["offer_prices"],
                           daily_data["categories"], color_map, "Items sold — today")
        if daily_data else None
    )
    daily_cat_names, daily_cat_revenue = _category_revenue(Purchase.objects.filter(purchased_at__gte=since_1))
    daily_pie = render_pie_chart(daily_cat_names, daily_cat_revenue, color_map, "Revenue by category — today")

    # Weekly 
    since_7 = now - timedelta(days=7)
    weekly_data = _item_breakdown(Purchase.objects.filter(purchased_at__gte=since_7))
    weekly_chart = (
        render_item_chart(weekly_data["names"], weekly_data["regular_units"], weekly_data["regular_prices"],
                           weekly_data["offer_units"], weekly_data["offer_prices"],
                           weekly_data["categories"], color_map, "Items sold — this week")
        if weekly_data else None
    )
    weekly_cat_names, weekly_cat_revenue = _category_revenue(Purchase.objects.filter(purchased_at__gte=since_7))
    weekly_pie = render_pie_chart(weekly_cat_names, weekly_cat_revenue, color_map, "Revenue by category — this week")

    # ---- Monthly ----
    since_30 = now - timedelta(days=30)
    monthly_data = _item_breakdown(Purchase.objects.filter(purchased_at__gte=since_30))
    monthly_chart = (
        render_item_chart(monthly_data["names"], monthly_data["regular_units"], monthly_data["regular_prices"],
                           monthly_data["offer_units"], monthly_data["offer_prices"],
                           monthly_data["categories"], color_map, "Items sold — this month")
        if monthly_data else None
    )
    monthly_cat_names, monthly_cat_revenue = _category_revenue(Purchase.objects.filter(purchased_at__gte=since_30))
    monthly_pie = render_pie_chart(monthly_cat_names, monthly_cat_revenue, color_map, "Revenue by category — this month")

    # ---- Restock needed — numpy-vectorized sales-velocity calculation ----
    since_window = now - timedelta(days=SALES_WINDOW_DAYS)
    sales_map = dict(
        Purchase.objects.filter(purchased_at__gte=since_window)
        .values("product_id")
        .annotate(units=Sum("quantity"))
        .values_list("product_id", "units")
    )

    products = list(Product.objects.select_related("category").all())
    product_ids = np.array([p.id for p in products])
    quantities = np.array([p.quantity for p in products], dtype=float)
    units_sold = np.array([sales_map.get(pid, 0) for pid in product_ids], dtype=float)

    avg_daily = units_sold / SALES_WINDOW_DAYS
    with np.errstate(divide="ignore", invalid="ignore"):
        days_left = np.where(avg_daily > 0, quantities / avg_daily, np.nan)

    needs_restock_mask = (np.nan_to_num(days_left, nan=np.inf) <= RESTOCK_LEAD_DAYS) | (quantities == 0)

    restock_items = []
    for i, product in enumerate(products):
        if needs_restock_mask[i]:
            dl = days_left[i]
            restock_items.append({
                "product": product,
                "days_left": None if np.isnan(dl) else round(float(dl), 1),
                "avg_daily": round(float(avg_daily[i]), 1),
            })

    restock_items.sort(key=lambda x: (x["days_left"] is None, x["days_left"] or 0))

    restock_by_category = {}
    for item in restock_items:
        cat_name = item["product"].category.name if item["product"].category else "Other"
        restock_by_category.setdefault(cat_name, []).append(item)

    active_offers = Product.objects.filter(is_trashed=False, offer_percent__gt=0)\
    .select_related("category").order_by("offer_percent")



    return render(request, "DBstore/dashboard.html", {
        "daily_chart": daily_chart,
        "weekly_chart": weekly_chart,
        "monthly_chart": monthly_chart,
        "daily_pie": daily_pie,
        "weekly_pie": weekly_pie,
        "monthly_pie": monthly_pie,
        "restock_by_category": restock_by_category,
        "restock_lead_days": RESTOCK_LEAD_DAYS,
        "active_offers" :active_offers,
    })