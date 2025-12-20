from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from datetime import date

# --- 1. 保存場所マスタテーブル (Location) ---
class Location(models.Model):
    name = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="保存場所名")

    class Meta:
        verbose_name = "保存場所マスタ"
        verbose_name_plural = "保存場所マスタ一覧"

    def __str__(self):
        return self.name

# --- 2. 食材カテゴリマスタ (Category) ---
# IngredientとFixedIngredientが参照するため、先に定義します。
class Category(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="食材カテゴリ名"
    )

    class Meta:
        verbose_name = "食材カテゴリマスタ"
        verbose_name_plural = "食材カテゴリマスタ一覧"

    def __str__(self):
        return self.name

# --- 3. 固定食材マスタ (FixedIngredient) ---
class FixedIngredient(models.Model):
    """固定食材（テンプレートアイテム）のマスタ"""
    name = models.CharField(max_length=100, unique=True, verbose_name='固定食材名')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='カテゴリ')

    is_quick_add = models.BooleanField(default=False, verbose_name='クイック追加対象')
    default_quantity = models.PositiveIntegerField(default=1, verbose_name='デフォルト数量')
    default_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='デフォルト保存場所')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '固定食材マスタ'
        verbose_name_plural = '固定食材マスタ'


# --- 4. 食材管理テーブル (Ingredient) ---
# ユーザーごとの実際の食材データです。Category と Location を参照します。
class Ingredient(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="ユーザーID"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="食材カテゴリID"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        verbose_name="保存場所ID"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="食材名"
    )
    expiry_date = models.DateField(
        verbose_name="賞味期限/消費期限"
    )
    quantity = models.IntegerField(
        default=1,
        verbose_name="数量"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='金額'
    )
    store_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='購入店舗'
    )
    registered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="登録日時"
    )
    @property
    def days_left(self):
        """期限までの残り日数"""
        return (self.expiry_date - date.today()).days

    @property
    def status_class(self):
        """色分け用のCSSクラス"""
        if self.days_left < 0:
            return "expired"      # 赤
        elif self.days_left <= 3:
            return "danger"       # オレンジ
        elif self.days_left <= 7:
            return "warning"      # 黄色
        return "safe"             # 通常

    class Meta:
        # 賞味期限が近い順に並べる
        ordering = ['expiry_date']
        verbose_name = "食材管理"
        verbose_name_plural = "食材管理一覧"

    def __str__(self):
        return f"{self.name} ({self.quantity}) - Expires on {self.expiry_date}"

class UsageHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="ユーザーID"
    )
    # 削除された食材の名前を記録
    item_name = models.CharField(
        max_length=100,
        verbose_name="食材名"
    )
    # 削除された食材のカテゴリも記録 (履歴をカテゴリで絞り込む場合を想定)
    category_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="食材カテゴリ"
    )
    # どの程度の数量が使用（削除）されたか
    quantity_used = models.PositiveIntegerField(
        verbose_name="使用数量"
    )
    # いつ使用されたか
    used_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="使用日時"
    )
    # 削除・使用時の賞味期限
    expiry_date_at_usage = models.DateField(
        null=True,
        blank=True,
        verbose_name="使用時の賞味期限"
    )
    price_at_usage = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='購入時金額'
    )
    store_name_at_usage = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='購入店舗'
    )

    class Meta:
        ordering = ['-used_at'] # 新しい履歴が上に来るように降順にソート
        verbose_name = "食材使用履歴"
        verbose_name_plural = "食材使用履歴一覧"

    def __str__(self):
        return f"{self.item_name} ({self.quantity_used}) used by {self.user.username}"

class Recipe(models.Model):
    # 外部APIで識別するためのID (例: 楽天レシピID)。ユニークな値として扱う。
    recipe_id = models.CharField(max_length=100, unique=True, verbose_name="レシピID")
    
    # レシピ名
    title = models.CharField(max_length=200, verbose_name="レシピ名")
    
    # レシピのURL
    url = models.URLField(verbose_name="レシピURL")
    
    # 画像のURL
    image_url = models.URLField(null=True, blank=True, verbose_name="画像URL")
    
    # 概算の調理時間 (例: 15分, 30分など)
    cooking_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="調理時間")
    
    # レシピの概要や説明 (任意)
    description = models.TextField(null=True, blank=True, verbose_name="概要")
    
    # **【重要】** そのレシピに必要な主な食材を格納するフィールド
    required_ingredients_text = models.TextField(verbose_name="必要食材リスト", help_text="カンマ区切りなどで必要な食材を保存")

    # ユーザーがお気に入り登録したかどうか (今回は使用しませんが、将来のために残しておきます)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="ユーザー", null=True)
    is_favorite = models.BooleanField(default=False, verbose_name="お気に入り")
    
    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "レシピ"
        verbose_name_plural = "レシピ"