# items/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Location, Ingredient, Category, FixedIngredient, UsageHistory
from .forms import IngredientForm
from datetime import date, timedelta
from django.views.generic import UpdateView, DeleteView
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect
from datetime import date
from django.db.models import Sum, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from django.core.exceptions import FieldDoesNotExist
from django.contrib import messages
from .models import Ingredient, Category, Recipe
from django.views import View
from .api_connector import KurashiruConnector

# トップページ）画面
@login_required
def home(request):
    today = date.today()
    one_week_later = today + timedelta(days=7)
    quick_add_items = FixedIngredient.objects.filter(is_quick_add=True)

    item_list = Ingredient.objects.filter(
        user=request.user,
        expiry_date__gte=today,
        expiry_date__lte=one_week_later
    ).order_by('expiry_date')

    item_list_all = Ingredient.objects.filter(
        user=request.user
    ).order_by('expiry_date')

    context = {
        'item_list': item_list,
        'one_week_later': one_week_later,
        'quick_add_items': quick_add_items,
    }
    return render(request, 'index.html', context)

# サインアップ画面
class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

# 食材登録画面
@method_decorator(login_required, name='dispatch')
class IngredientCreateView(CreateView):
    model = Ingredient
    form_class = IngredientForm
    success_url = reverse_lazy('item_list')
    template_name = 'items/item_form.html'

    def get_initial(self):
        # 1. 親クラスのget_initialを呼び出す (name, category以外のデフォルト値を期待)
        initial = super().get_initial()

        # 🌟 最終修正点: locationのデフォルト値を強制的にセット 🌟
        # ★★★ ここに、管理者サイトでデフォルトにした場所のIDを直接入力してください ★★★
        DEFAULT_LOCATION_ID = 1  # 例: 冷蔵庫のIDが 1 だと仮定
        
        # locationの初期値が空の場合のみ、デフォルトIDを設定
        if 'location' not in initial or initial['location'] is None:
             initial['location'] = DEFAULT_LOCATION_ID

        # 2. URLパラメータから name と category の値を取得
        initial_name = self.request.GET.get('name')
        initial_category_id = self.request.GET.get('category')
        
        # 3. URLパラメータの値を initial 辞書に追加（上書き）
        if initial_name:
            initial['name'] = initial_name
        
        if initial_category_id and initial_category_id.isdigit():
            initial['category'] = initial_category_id
        
        print("★★★ フォームにセットされる最終初期値: ", initial)
        
        return initial
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

# 期限が近い食材一覧画面
@method_decorator(login_required, name='dispatch')
class IngredientListView(ListView):
    model = Ingredient
    template_name = 'items/item_list.html'
    context_object_name = 'item_list'

    def get_queryset(self):
        queryset = Ingredient.objects.filter(user=self.request.user).order_by('expiry_date')

        category_id = self.request.GET.get('category')
        if category_id:
            try:
                queryset = queryset.filter(category_id=category_id)
            except ValueError:
                pass

        today = date.today()
        
        for ingredient in queryset:
            if ingredient.expiry_date:
                remaining_days = (ingredient.expiry_date - today).days
                ingredient.remaining_days = remaining_days

                if remaining_days < 0:
                    ingredient.expired_days = abs(remaining_days)
                else:
                    ingredient.expired_days = 0
            else:
                ingredient.remaining_days = None
                ingredient.expired_days = None
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        return context
    
#食材データの編集更新
@method_decorator(login_required, name='dispatch')
class IngredientUpdateView(UpdateView):
    model = Ingredient
    form_class = IngredientForm
    success_url = reverse_lazy('item_list')
    template_name = 'items/item_form.html'

    def form_valid(self, form):
        other_location_name = form.cleaned_data.get('other_location')
        OTHER_LOCATION_NAME = 'その他'
        if form.instance.location.name == OTHER_LOCATION_NAME and other_location_name:
            new_location, created = Location.objects.get_or_create(
                name=other_location_name
            )
            form.instance.location = new_location

        form.instance.user = self.request.user
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class IngredientDeleteView(DeleteView):
    model = Ingredient
    success_url = reverse_lazy('item_list')
    template_name = 'items/item_confirm_delete.html'

@login_required
def use_item(request, pk):
    if request.method == 'POST':
        try:
            ingredient = Ingredient.objects.get(pk=pk, user=request.user)
        except Ingredient.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('item_list'))

        if ingredient.quantity > 1:
            ingredient.quantity -= 1
            ingredient.save()
        else:
            ingredient.delete()
        return HttpResponseRedirect(reverse_lazy('item_list'))
    return HttpResponseRedirect(reverse_lazy('item_list'))

#在庫数変更
@login_required
def update_ingredient_quantity(request, pk):
    if request.method == 'POST':
        try:
            used_amount = int(request.POST.get('used_amount', 1))
        except (TypeError, ValueError):
            return HttpResponseRedirect(reverse_lazy('item_list'))

        if used_amount <= 0:
            return HttpResponseRedirect(reverse_lazy('item_list'))

        try:
            ingredient = Ingredient.objects.get(pk=pk, user=request.user)
        except Ingredient.DoesNotExist:
            return HttpResponseRedirect(reverse_lazy('item_list'))

        if ingredient.quantity > used_amount:
            # 数量が減る場合
            ingredient.quantity -= used_amount
            ingredient.save()

            # 履歴の作成
            UsageHistory.objects.create(
                user=request.user,
                item_name=ingredient.name,
                category_name=ingredient.category.name if ingredient.category else None,
                quantity_used=used_amount,
                expiry_date_at_usage=ingredient.expiry_date,
                price_at_usage=ingredient.price if ingredient.price is not None else 0, # 金額がない場合は0を渡す
                store_name_at_usage=ingredient.store_name
            )

        else:
            # 全て使用され、削除される場合
            total_used = ingredient.quantity

            # 履歴の作成
            UsageHistory.objects.create(
                user=request.user,
                item_name=ingredient.name,
                category_name=ingredient.category.name if ingredient.category else None,
                quantity_used=total_used,
                expiry_date_at_usage=ingredient.expiry_date,
                price_at_usage=ingredient.price if ingredient.price is not None else 0,
                store_name_at_usage=ingredient.store_name
            )
            ingredient.delete()
        return HttpResponseRedirect(reverse_lazy('item_list'))

@login_required
def quick_add_ingredient(request, fixed_pk):
    """固定食材IDを使って、ワンタップで食材を登録し、編集画面へリダイレクトする"""
    if request.method != 'POST':
        return redirect('home')

    try:
        fixed_item = FixedIngredient.objects.get(pk=fixed_pk)
    except FixedIngredient.DoesNotExist:
        return redirect('item_list')

    new_ingredient = Ingredient.objects.create(
        user=request.user,
        name=fixed_item.name,
        category=fixed_item.category,
        location=fixed_item.default_location,
        quantity=fixed_item.default_quantity,
        expiry_date=date.today()
    )
    return redirect('item_edit', pk=new_ingredient.pk)

@login_required
def add_ingredient(request):
    fixed_items = FixedIngredient.objects.all()
    if request.method == 'POST':
        fixed_item_id = request.POST.get('fixed_item_id')
        if fixed_item_id:
            try:
                fixed_item = FixedIngredient.objects.get(id=fixed_item_id)
                Ingredient.objects.create(
                    user=request.user,
                    name=fixed_item.name,
                    category=fixed_item.category,
                    location=fixed_item.default_location,
                    quantity=fixed_item.default_quantity,
                    expiry_date=date.today()
                )
                return redirect('item_list')

            except FixedIngredient.DoesNotExist:
                pass

        form = IngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.user = request.user
            other_location_name = form.cleaned_data.get('other_location')
            OTHER_LOCATION_NAME = 'その他'

            if ingredient.location and ingredient.location.name == OTHER_LOCATION_NAME and other_location_name:
                new_location, created = Location.objects.get_or_create(
                    name=other_location_name
                )
                ingredient.location = new_location

            ingredient.save()
            return redirect('item_list')

    else:
        form = IngredientForm()

    context = {
        'form': form,
        'fixed_items': fixed_items,
    }
    return render(request, 'items/item_form.html', context)

@method_decorator(login_required, name='dispatch')
class QuickAddListView(ListView):
    """クイック追加用固定食材の一覧表示"""
    model = FixedIngredient
    template_name = 'items/item_quick_add_list.html'
    context_object_name = 'fixed_ingredients'

    def get_queryset(self):
        # 管理者設定された固定食材（クイック追加対象）のみをフィルタリング
        return FixedIngredient.objects.filter(is_quick_add=True).order_by('name')

@method_decorator(login_required, name='dispatch')
class UsageHistoryListView(ListView):
    model = UsageHistory
    template_name = 'items/usage_history.html'
    context_object_name = 'history_list'

    # 1. 履歴リスト本体の取得 (get_queryset)
    def get_queryset(self):
        # 自分の使用履歴のみを表示
        return UsageHistory.objects.filter(user=self.request.user).order_by('-used_at')
    # 2. 集計データの作成 (get_context_data)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_history = UsageHistory.objects.filter(user=self.request.user)

        # 月ごとの合計支出額を計算
        monthly_spend = user_history.annotate(
            month=TruncMonth('used_at')
        ).values('month').annotate(
            total_price=Sum(Coalesce('price_at_usage', 0.0, output_field=DecimalField())) 
        ).order_by('-month')

        # カテゴリ別の合計支出額を計算
        category_spend = user_history.values('category_name').annotate(
            total_price=Sum(Coalesce('price_at_usage', 0.0, output_field=DecimalField()))
        ).exclude(category_name__isnull=True).order_by('-total_price')

        context['monthly_spend'] = monthly_spend
        context['category_spend'] = category_spend

        return context

@login_required
def item_bulk_operation(request):
    """選択された食材に対して一括操作（削除、使用など）を実行する"""
    if request.method == 'POST':
        selected_pks = request.POST.getlist('selected_items')
        action = request.POST.get('action')

        if not selected_pks:
            messages.warning(request, '操作対象の食材が選択されていません。')
            return redirect('item_list')

        # 選択されたPKを持つ食材をユーザーに紐づけてフィルタリング
        items_to_operate = Ingredient.objects.filter(
            pk__in=selected_pks,
            user=request.user
        ).order_by('-pk') # 削除時にリストが崩れるのを防ぐため逆順にソート

        if action == 'delete':
            count, _ = items_to_operate.delete()
            messages.success(request, f'{count} 件の食材を削除しました。')

        elif action == 'use':
            used_count = 0
            for ingredient in items_to_operate:
                if ingredient.quantity > 0:
                    UsageHistory.objects.create(
                        user=request.user,
                        item_name=ingredient.name,
                        category_name=ingredient.category.name if ingredient.category else None,
                        quantity_used=1,
                        expiry_date_at_usage=ingredient.expiry_date,
                        price_at_usage=ingredient.price if ingredient.price is not None else 0, 
                        store_name_at_usage=ingredient.store_name
                    )
                    used_count += 1

                    if ingredient.quantity > 1:
                        # 数量を減らす
                        ingredient.quantity -= 1
                        ingredient.save()
                    else:
                        # 全て使用されたので削除
                        ingredient.delete()

            messages.success(request, f'{used_count} 件の食材を1つずつ使用済みにしました。')

        else:
            messages.error(request, '無効な操作が指定されました。')
    return redirect('item_list')

# views.py の ItemListView
@method_decorator(login_required, name='dispatch')
class ItemListView(ListView):
    model = Ingredient
    template_name = 'items/item_list.html'
    context_object_name = 'item_list'
    
    # 1. 食材リスト（メインデータ）の取得ロジック
    def get_queryset(self):
        # ユーザーに紐づく Ingredient を取得（Ingredientモデルに 'user' フィールドがあるためOK）
        queryset = self.model.objects.filter(user=self.request.user)
        
        # URLパラメータからカテゴリIDを取得
        category_id = self.request.GET.get('category')
        
        # カテゴリで絞り込み
        if category_id:
            queryset = queryset.filter(category__id=category_id)
        
        # 賞味期限が近い順に並べる
        return queryset.order_by('expiry_date')

    # 2. テンプレートに渡す追加データ（カテゴリ、数量オプション）の設定ロジック
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print("\n--- [DEBUG START] get_context_data 実行 ---")
        context['categories'] = Category.objects.all().order_by('name') 
        context['selected_category'] = self.request.GET.get('category', '')
        context['quantity_options'] = range(1, 11)

        print(f"DEBUG: quantity_options 中身: {list(context['quantity_options'])}")
        print("--- [DEBUG END] -------------------------\n")
        return context

@method_decorator(login_required, name='dispatch')
class RecipeSearchView(ListView):
    template_name = 'items/recipe_search.html'
    context_object_name = 'recommended_recipes'
    model = Recipe

    def get_queryset(self):
        # ユーザーの全在庫食材を取得 (🚨 デバッグ: フィルタリングを解除)
        user_ingredients = Ingredient.objects.all() 
        ingredient_names = list(user_ingredients.values_list('name', flat=True))

        if not ingredient_names:
            print("DEBUG: 在庫ゼロのためAPI呼び出しをスキップ")
            return []
class ManualRecipeSearchView(View):
    def get(self, request):
        keyword = request.GET.get("ingredients", "").strip()
        recipes = []
        if keyword:
            connector = KurashiruConnector()
            recipes = connector.search_recipes(keyword)

            print("--- 手動検索デバッグ ---")
            print(f"検索食材: {keyword}")
            print(f"結果のレシピ数: {len(recipes)}")

        # 在庫食材を取得（ユーザーに紐づけるなら filter(user=request.user)）
        item_list = Ingredient.objects.filter(user=request.user)

        context = {
            "keyword": keyword,
            "recipes": recipes,
            "item_list": item_list,
        }
        return render(request, "items/recipe_search.html", context)