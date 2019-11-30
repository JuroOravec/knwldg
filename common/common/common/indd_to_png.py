import argparse
from io import BytesIO
import time

from PIL import Image
import selenium.webdriver


FORMATS = ['pdf', 'png']
OUTFILE_DEFAULT = 'convert_indd_export'
WD_DEFAULT = 'chrome'
WD_ARGS_DEFAULT = '--start-maximized'
DELAY = 0.5


def _get_indd_slide_url(wd):
    wd.switch_to.frame(wd.find_element_by_name('targetFrame'))
    wd.switch_to.frame(wd.find_element_by_name('targetFrame0'))
    url = wd.execute_script('return location.href')
    wd.switch_to.default_content()
    return url


def _get_indd_next_slide_el(wd):
    return wd.find_element_by_xpath('//div[@id="nextPageBtn"]')


def _is_indd_last_slide(wd):
    el = _get_indd_next_slide_el(wd)
    return el.value_of_css_property('display') != 'block'


def _load_indd_next_slide(wd):
    btn_wrap = _get_indd_next_slide_el(wd)
    next_slide_btn = btn_wrap.find_element_by_tag_name('button')
    wd.execute_script("arguments[0].click();", next_slide_btn)


def _make_indd_slide_screenshot(wd):
    body = wd.find_element_by_tag_name('body')
    image = body.screenshot_as_png
    img = Image.open(BytesIO(image))
    return img


def convert_indd(url, format=FORMATS[0], outfile=OUTFILE_DEFAULT,
                 webdriver=WD_DEFAULT, webdriver_args=WD_ARGS_DEFAULT,
                 delay=DELAY,
                 slide_url_extractor=None, next_slide_loader=None,
                 last_slide_predicate=None, slide_screenshotter=None):

    if format not in FORMATS:
        raise ValueError('Output format must be one of {formats}.'.format(
            formats="'" + "', '".join(FORMATS) + "'"))

    if slide_url_extractor is None:
        slide_url_extractor = _get_indd_slide_url
    if last_slide_predicate is None:
        last_slide_predicate = _is_indd_last_slide
    if next_slide_loader is None:
        next_slide_loader = _load_indd_next_slide
    if slide_screenshotter is None:
        slide_screenshotter = _make_indd_slide_screenshot

    try:
        module = getattr(selenium.webdriver, webdriver)
        WebDriver = module.webdriver.WebDriver
        Options = module.options.Options
    except Exception as e:
        raise ValueError(f"Unrecognized WebDriver '{webdriver}'") from e

    options = Options()
    for arg in webdriver_args.strip().split():
        options.add_argument(arg)
    with WebDriver(options=options) as wd:
        wd.get(url)
        slide_urls = []
        while True:
            slide_urls.append(slide_url_extractor(wd))
            if last_slide_predicate(wd):
                break
            next_slide_loader(wd)
            time.sleep(delay)

        imgs = []
        for url in slide_urls:
            wd.get(url)
            imgs.append(slide_screenshotter(wd))

        if format == 'pdf':
            def rgba_to_rgb(rgba):
                # https://stackoverflow.com/a/50772549/9788634
                rgb = Image.new('RGB', rgba.size, (255, 255, 255))
                rgb.paste(rgba, mask=rgba.split()[3])
                return rgb

            rgb_imgs = list(map(rgba_to_rgb, imgs))
            img = rgb_imgs.pop(0)
            # https://stackoverflow.com/a/47283224/9788634
            img.save(f'{outfile}.pdf', "PDF", resolution=100.0,
                     save_all=True, append_images=rgb_imgs)

        else:
            for i, img in enumerate(imgs):
                img.save(f'{outfile}_{i + 1}.{format}')


def main():
    parser = argparse.ArgumentParser(description='Download a published Adobe '
                                     'InDesign document in a specific format.')
    parser.add_argument('url', help='URL of the Adobe InDesign document')
    parser.add_argument('-o', '--outfile', default=OUTFILE_DEFAULT, help='Name'
                        " of the output file(s). Default: '{default}'".format(
                            default=OUTFILE_DEFAULT))
    parser.add_argument('-f', '--format', choices=FORMATS, default=FORMATS[0],
                        help='Format of the output file(s). Accepted formats: '
                        "{formats}. Default: '{default}'".format(
                            formats="'" + "', '".join(FORMATS) + "'",
                            default=FORMATS[0]))
    parser.add_argument('-w', '--webdriver', default=WD_DEFAULT,
                        help='Webdrive to use with Selenium. Default: '
                        "'{default}'".format(default=WD_DEFAULT))
    parser.add_argument('-a', '--webdriver-args', default=WD_ARGS_DEFAULT,
                        help='Arguments passed to Webdriver. Default: '
                        "'{default}'".format(default=WD_ARGS_DEFAULT))
    parser.add_argument('-d', '--delay', default=DELAY, type=float,
                        help='Delay in seconds given to load a next slide. '
                        "Default: {default}s".format(default=DELAY))

    args = vars(parser.parse_args())
    convert_indd(**args)


if __name__ == '__main__':
    main()
