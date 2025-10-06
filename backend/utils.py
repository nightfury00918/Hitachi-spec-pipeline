import numpy as np
import pandas as pd
import math

def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN and Inf with None so FastAPI can serialize safely."""
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.where(pd.notnull(df), None)
    return df


def clean_for_json(obj):
    """Recursively replace NaN/Inf with None so FastAPI can return safe JSON."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj
