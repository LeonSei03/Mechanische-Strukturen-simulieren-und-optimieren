from io import BytesIO
from PIL import Image

def fig_zu_pil(fig, dpi=120):
    """Funktion um eine Matplotlib Figur zu einem PIL Image umzuwandeln"""
    buf = BytesIO()
    fig.savefig(buf,format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return Image.open(buf).convert("RGB")

def pil_liste_zu_gif(images, duration_ms=120):
    """Funktion um aus einer Liste an PIL Bildern einen Gif zu erstellen"""

    if not images:
        return None
    
    buf = BytesIO()
    images[0].save(buf, format="GIF", save_all=True, append_images=images[1:], duration=duration_ms, loop=0)
    buf.seek(0)
    return buf.getvalue()