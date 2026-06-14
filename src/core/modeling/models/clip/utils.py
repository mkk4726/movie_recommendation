from PIL import Image


def make_square(image: Image.Image, fill_color=(0, 0, 0)) -> Image.Image:
    x, y = image.size
    size = max(x, y)
    new_image = Image.new("RGB", (size, size), fill_color)
    new_image.paste(image, ((size - x) // 2, (size - y) // 2))
    return new_image
