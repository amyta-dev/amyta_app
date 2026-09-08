"""
Auto-discovery helper untuk sidebar Jazzmin.

Karena sekarang hanya core.accounts yang punya model persisten (semua
fitur review perpajakan lain bersifat stateless, diproses dalam satu
request di apps.tax_review), file ini disederhanakan. Kalau nanti ada
app baru yang memang butuh model persisten + halaman admin sendiri,
tambahkan `feature_menu` di apps.py-nya dan app tsb otomatis kedaftar
lewat fungsi ini.
"""
from django.apps import apps as django_apps


def get_registered_features():
    features = []
    for app_config in django_apps.get_app_configs():
        if app_config.name.startswith("apps."):
            feature_menu = getattr(app_config, "feature_menu", None)
            if feature_menu:
                features.append({"app_label": app_config.label, **feature_menu})
    return features
