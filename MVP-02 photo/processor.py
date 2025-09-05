from rembg import remove
from PIL import Image, ImageOps
import numpy as np
import cv2

# 目标画布/规范（近似）
CANVAS = 1200  # 1200x1200 px
TARGET_HEAD = 750  # 目标头部高度（px），约等价 1.25 英寸
TARGET_EYES_FROM_BOTTOM = 750  # 目标眼睛高度（px）≈ 1.25 英寸
WHITE = (255, 255, 255)

def _ensure_white_bg(img: Image.Image) -> Image.Image:
    """用 rembg 去背景后，合成纯白背景；并裁掉多余留白边界。"""
    # rembg: 输入/输出为 RGBA（带 alpha）
    rgba = remove(img)
    if rgba.mode != "RGBA":
        rgba = rgba.convert("RGBA")

    # 合成到白底
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    comp = Image.alpha_composite(white_bg, rgba).convert("RGB")

    # 根据 alpha 的非空区域裁切（收紧边界）
    alpha = np.array(rgba.split()[-1])
    ys, xs = np.where(alpha > 10)
    if len(xs) == 0 or len(ys) == 0:
        return comp  # 没抠到就直接返回
    x1, x2 = xs.min(), xs.max()
    y1, y2 = ys.min(), ys.max()
    comp_cropped = comp.crop((x1, y1, x2 + 1, y2 + 1))
    return comp_cropped

def _detect_face_bbox(img_rgb: Image.Image):
    """使用 OpenCV HaarCascade 检测人脸，返回 (x, y, w, h)；检测失败返回 None。"""
    cv_img = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    # 使用 OpenCV 自带级联分类器
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades +
                                         "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1,
                                          minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    # 取最大的人脸框
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    return faces[0]  # (x, y, w, h)

def _pad_to_fit(img: Image.Image, w: int, h: int, bg=WHITE) -> Image.Image:
    """若后续裁剪会越界，则先给图像外扩白边。"""
    iw, ih = img.size
    pad_w = max(0, w - iw)
    pad_h = max(0, h - ih)
    if pad_w == 0 and pad_h == 0:
        return img
    left = pad_w // 2
    right = pad_w - left
    top = pad_h // 2
    bottom = pad_h - top
    return ImageOps.expand(img, border=(left, top, right, bottom), fill=bg)

def process_passport_photo(src_img: Image.Image) -> Image.Image:
    """
    核心流程：
    1) rembg 抠图 + 白底合成 + 收紧边界
    2) 检测人脸框，估计“头部高度”（用脸高近似，保守放大）
    3) 按目标头高缩放
    4) 布局：将“眼睛”近似放置在距底部 TARGET_EYES_FROM_BOTTOM
    5) 居中裁剪 1200×1200，越界则自动白边填充
    """
    # 1) 白底与裁边
    img = _ensure_white_bg(src_img)

    # 2) 人脸检测
    face = _detect_face_bbox(img)
    iw, ih = img.size

    if face is None:
        # 检测不到脸：退化策略——按主体整体框估计（用全图）
        # 直接居中缩放使主体高度接近 TARGET_HEAD
        scale = TARGET_HEAD / ih
        new_w = int(round(iw * scale))
        new_h = int(round(ih * scale))
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        # 以“头顶 ~ 眼睛 ~ 下巴”未知为前提，采用略靠上的布置
        # 构造比画布更大的底图以便裁剪
        base = _pad_to_fit(img_resized, CANVAS, CANVAS * 2)
        bw, bh = base.size
        # 使主体大致位于画布下半部，接近目标眼高
        top = max(0, int(bh//2 - CANVAS))
        crop = base.crop((bw//2 - CANVAS//2, top, bw//2 + CANVAS//2, top + CANVAS))
        return crop

    # 3) 以人脸高度作为“头部高度”近似，并做一点增益让头顶+下巴有余量
    x, y, w, h = face
    head_h_est = h * 1.15  # 估计头顶-下巴略大于脸框（15%冗余）
    scale = TARGET_HEAD / head_h_est
    new_w = int(round(iw * scale))
    new_h = int(round(ih * scale))
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # 4) 计算眼睛大致位置（用人脸框内眼睛高度经验：距脸顶约 0.4*h）
    #    然后把“眼睛”放到距底部 TARGET_EYES_FROM_BOTTOM
    rx = int(round(x * scale))
    ry = int(round(y * scale))
    rw = int(round(w * scale))
    rh = int(round(h * scale))

    # 估计眼睛 y 坐标（在缩放后图上）
    eye_y_est = ry + int(round(0.4 * rh))

    # 我们想要： (crop_bottom - eye_y_est) == TARGET_EYES_FROM_BOTTOM
    #  => crop_bottom = eye_y_est + TARGET_EYES_FROM_BOTTOM
    crop_bottom = eye_y_est + TARGET_EYES_FROM_BOTTOM
    crop_top = crop_bottom - CANVAS

    # 水平居中裁剪
    cx_center = img_resized.width // 2
    left = cx_center - CANVAS // 2
    right = left + CANVAS

    # 5) 若裁剪越界则先外扩白边
    need_w = max(CANVAS, right, img_resized.width) - min(0, left)
    need_h = max(CANVAS, crop_bottom, img_resized.height) - min(0, crop_top)
    pad_needed = (
        left < 0 or right > img_resized.width or
        crop_top < 0 or crop_bottom > img_resized.height
    )
    base = img_resized
    if pad_needed:
        # 计算所需最小画布尺寸（左右/上下留白）
        extra_w = max(0, -left) + max(0, right - img_resized.width)
        extra_h = max(0, -crop_top) + max(0, crop_bottom - img_resized.height)
        pad_w = img_resized.width + extra_w
        pad_h = img_resized.height + extra_h
        base = _pad_to_fit(img_resized, pad_w, pad_h, bg=WHITE)

        # pad 后，坐标整体平移
        shift_x = (pad_w - img_resized.width) // 2
        shift_y = (pad_h - img_resized.height) // 2
        left += shift_x
        right += shift_x
        crop_top += shift_y
        crop_bottom += shift_y

    # 最终裁剪
    crop = base.crop((left, crop_top, right, crop_bottom))

    # 写死输出为 1200×1200（保险处理）
    if crop.size != (CANVAS, CANVAS):
        crop = crop.resize((CANVAS, CANVAS), Image.LANCZOS)
    return crop
