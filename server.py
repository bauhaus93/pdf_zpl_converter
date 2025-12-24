#!/usr/bin/env python3
import logging
import sys
from io import BytesIO
from timeit import default_timer as timer

import numpy as np
from fastcgi import fastcgi
from pdf2image import convert_from_bytes
from pypdf import PdfReader
from zebrafy import ZebrafyImage, ZebrafyPDF

# good:         306x432 @ 72 dpi= 4.25x6.0 in
# bad & ugly:   595.27x841.68 @ 72 dpi = 8.26x11.69 in

# @ 203 DPI, we should have that many points on a label
PRINTER_DOTS_WIDTH = 832
PRINTER_DOTS_HEIGHT = 1218

FORMAT = "Z64"

logging.basicConfig(
    # filename="pdf_converter.log",
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
)
_logger = logging.getLogger(__name__)


def _is_a4(width_dots, height_dots, tolerance=5.0):
    return abs(width_dots - 595) < tolerance and abs(height_dots - 842) < tolerance


def _get_rect(img, padding=10):
    a = np.asarray(img)
    left, top, right, bottom = 0, 0, a.shape[1], a.shape[0]

    for i in range(left, right):
        if not a[:, i].all():
            left = i
            break
    for i in reversed(range(left, right)):
        if not a[:, i].all():
            right = i
            break
    for i in range(top, bottom):
        if not a[i, :].all():
            top = i
            break
    for i in reversed(range(top, bottom)):
        if not a[i:].all():
            bottom = i
            break

    return (
        max(0, left - padding),
        max(0, top - padding),
        min(a.shape[1], right + padding),
        min(a.shape[0], bottom + padding),
    )


def _quarter_pages_to_zpl_images(pdf):
    result = []
    for img in convert_from_bytes(pdf):
        _logger.info(
            "Quartering pdf page of size %dx%d to zpl images", img.width, img.height
        )
        divider_w = int(img.width // 2)
        divider_h = int(img.height // 2)
        for rect in [
            (0, 0, divider_w, divider_h),
            (0, divider_h, divider_w, img.height),
            (divider_w, 0, img.width, divider_h),
            (divider_w, divider_h, img.width, img.height),
        ]:
            quart = img.crop(rect)
            bw = quart.convert("L")
            ex = bw.getextrema()
            if ex[0] != ex[1]:
                shrinked_rect = _get_rect(bw)
                _logger.info(
                    "Shrinked rectangle from %dx%d down to %dx%d",
                    rect[2]-rect[0],
                    rect[3]-rect[1],
                    shrinked_rect[2]-shrinked_rect[0],
                    shrinked_rect[3]-shrinked_rect[1],
                )
                result.append(
                    ZebrafyImage(
                        quart.crop(shrinked_rect),
                        dither=False,
                        invert=True,
                        format=FORMAT,
                    ).to_zpl()
                )
            else:
                _logger.info(
                    "Quarter %d,%d,%d,%d is empty, do not add to result", *rect
                )
    return result

@fastcgi("/tmp/fcgi.sock")
def main():
    start = timer()

    raw_pdf = sys.stdin.buffer.read()

    pdf = PdfReader(BytesIO(raw_pdf))

    box = pdf.pages[0].mediabox
    units = pdf.pages[0].user_unit

    _logger.info(
        "Received pdf of size %.1fkB, box: %d,%d,%d,%d (%dx%d) user space units: %d",
        len(raw_pdf) / 1024,
        box.left,
        box.bottom,
        box.right,
        box.top,
        box.width,
        box.height,
        units,
    )

    if _is_a4(box.width, box.height):
        _logger.info(
            "PDF of dimensions %dx%d is assumed to be A4", box.width, box.height
        )
        imgs = _quarter_pages_to_zpl_images(raw_pdf)
        zpl = "".join(imgs[:4])
    else:
        width, height = box.width * units / 72, box.height * units / 72
        dpi = int(min(PRINTER_DOTS_WIDTH // width, PRINTER_DOTS_HEIGHT // height))
        _logger.info(
            "PDF of dimensions %dx%d is not assumed to be pdf, convert directly to zpl with %d dpi",
            box.width,
            box.height,
            dpi,
        )
        zpl = ZebrafyPDF(
            raw_pdf,
            invert=True,
            dither=False,
            split_pages=True,
            format=FORMAT,
            dpi=dpi,
        ).to_zpl()

    sys.stdout.write(f"Content-Type: text/plain\r\n\r\n{zpl}")
    t = timer() - start
    _logger.info(
        "Conversion of PDF of size %.1fkB to %.1fkB of zpl took %.2fms",
        len(raw_pdf) / 1024,
        len(zpl) / 1024,
        t * 1000.0,
    )


if __name__ == "__main__":
    main()
