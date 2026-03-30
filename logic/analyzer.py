import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import io
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def generate_feature_importance_plot(model, feature_names):
    """Генерация графика важности признаков для дерева решений"""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    plt.figure(figsize=(8, 5))
    sns.barplot(x=importances[indices], y=[feature_names[i] for i in indices], palette='viridis')
    plt.title('Важность признаков для рекомендаций', fontsize=14, fontweight='bold')
    plt.xlabel('Важность')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

def predict_progress(current_bmi, target_bmi):
    """Прогноз времени достижения цели по ИМТ"""
    if target_bmi < current_bmi:
        weekly_change = -0.15  # Снижение ИМТ на 0.15 в неделю при похудении
    elif target_bmi > current_bmi:
        weekly_change = 0.10   # Увеличение ИМТ на 0.10 в неделю при наборе массы
    else:
        return 0, current_bmi
    
    weeks_needed = abs(target_bmi - current_bmi) / abs(weekly_change)
    return int(np.ceil(weeks_needed)), target_bmi

def generate_progress_plot(current_bmi, target_bmi, weeks_needed):
    """Генерация графика прогноза прогресса"""
    weeks = list(range(weeks_needed + 1))
    
    if target_bmi < current_bmi:
        bmi_values = [current_bmi - 0.15 * w for w in weeks]
    else:
        bmi_values = [current_bmi + 0.10 * w for w in weeks]
    
    plt.figure(figsize=(10, 5))
    plt.plot(weeks, bmi_values, marker='o', linewidth=2, markersize=6, color='#2E86AB')
    plt.axhline(y=target_bmi, color='#A23B72', linestyle='--', label=f'Целевой ИМТ: {target_bmi}')
    plt.axhline(y=25.0, color='orange', linestyle=':', alpha=0.7, label='Граница избыточного веса')
    plt.axhline(y=18.5, color='green', linestyle=':', alpha=0.7, label='Граница нормы')
    
    plt.title('Прогноз изменения ИМТ', fontsize=14, fontweight='bold')
    plt.xlabel('Недели')
    plt.ylabel('ИМТ')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf