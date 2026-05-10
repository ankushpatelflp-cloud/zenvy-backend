from rembg import remove
from PIL import Image
from io import BytesIO

def remove_background(image_bytes):
    input_image = Image.open(BytesIO(image_bytes))

    output = remove(input_image)

    output_buffer = BytesIO()
    output.save(output_buffer, format="PNG")

    return output_buffer.getvalue()