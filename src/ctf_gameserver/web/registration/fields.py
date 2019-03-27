import os
import warnings
from urllib.parse import urljoin
from io import BytesIO

from django.db.models.fields.files import ImageField, ImageFieldFile
from django.forms.widgets import ClearableFileInput
from django.conf import settings
from django.utils.encoding import filepath_to_uri
from django.utils.html import conditional_escape, format_html
from PIL import Image

# Force an error when image decompression takes too much memory
Image.MAX_IMAGE_PIXELS = 2048*2048
warnings.simplefilter('error', Image.DecompressionBombWarning)


class ThumbnailImageFieldFile(ImageFieldFile):
    """
    Custom variant of ImageFieldFile which automatically generates a thumbnail when saving an image and
    stores the serialized PIL image instead of the raw input data to disk.
    """

    def save(self, name, content, *args, **kwargs):    # pylint: disable=arguments-differ
        # Can't use `content.image` because of https://code.djangoproject.com/ticket/30252
        image = Image.open(content)

        # We store a newly serialized version of the image, to (hopefully) prevent attacks where users
        # upload a valid image file that might also be interpreted as HTML/JS due to content sniffing.
        # If we didn't convert everything to PNG, we'd also have to take care to only allow file
        # extensions for which the web server sends a image/* mime type.
        data = BytesIO()
        image.save(data, 'PNG')
        data.seek(0)
        super().save(name, data, *args, **kwargs)

        thumbnail_data = BytesIO()
        thumbnail = image.copy()
        thumbnail.thumbnail(settings.THUMBNAIL_SIZE)
        thumbnail.save(thumbnail_data, 'PNG')
        thumbnail_data.seek(0)
        self.storage.save(self.get_thumbnail_path(), thumbnail_data)

    # Keep property of the parent method
    save.alters_data = True

    def delete(self, *args, **kwargs):    # pylint: disable=arguments-differ
        super().delete(*args, **kwargs)

        # This shouldn't fail if the thumbnail doesn't exist
        self.storage.delete(self.get_thumbnail_path())

    delete.alters_data = True

    def get_thumbnail_path(self):
        """
        Returns the path of the image's thumbnail version relative to the storage root (i.e. its "name" in
        storage system terms).
        Thumbnails have the same name as their original images stored in a 'thumbnails' directory alongside
        the original images.
        """
        path, filename = os.path.split(self.name)
        return os.path.join(path, 'thumbnails', filename)

    def get_thumbnail_url(self):
        """
        Returns the (absolute) URL for the image's thumbnail version.
        """
        return urljoin(settings.MEDIA_URL, filepath_to_uri(self.get_thumbnail_path()))


class ThumbnailImageField(ImageField):
    """
    Custom variant of ImageField which automatically resizes and re-serializes an uploaded image.
    """

    attr_class = ThumbnailImageFieldFile


class ClearableThumbnailImageInput(ClearableFileInput):
    """
    Custom variant of the ClearableFileInput widget for rendering a ThumbnailImageField. It will display the
    thumbnail image instead of the image's filename.
    """

    def get_template_substitution_values(self, value):
        return {
            'initial': format_html('<img class="clearable-input-image" src="{}" alt="{}" />',
                                   value.get_thumbnail_url(), str(value)),
            'initial_url': conditional_escape(value.url),
        }
