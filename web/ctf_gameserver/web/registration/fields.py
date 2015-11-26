import os
from urllib.parse import urljoin
from io import BytesIO

from django.db.models.fields.files import ImageField, ImageFieldFile
from django.forms.widgets import ClearableFileInput
from django.conf import settings
from django.utils.encoding import filepath_to_uri
from django.utils.html import conditional_escape, format_html
from PIL import Image


class ThumbnailImageFieldFile(ImageFieldFile):
    """
    Custom variant of ImageFieldFile which automatically generates a thumbnail when saving an image.
    """

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        thumbnail_data = BytesIO()

        image = Image.open(self.storage.open(self.name))
        image.thumbnail(settings.THUMBNAIL_SIZE)
        image.save(thumbnail_data, 'PNG')

        self.storage.save(self.get_thumbnail_path(), thumbnail_data)

    # Keep property of the parent method
    save.alters_data = True

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        # This shouldn't fail if the thumbnail doesn't exist
        self.storage.delete(self.get_thumbnail_path())

    delete.alters_data = True

    def get_thumbnail_path(self):
        """
        Returns the path of the image's thumbnail version relative to the storage root (i.e. its "name" in
        storage system terms).
        Thumbnails have the same base name as their original images with a '.png' extension and are stored in
        a 'thumbnails' directory alongside the original images.
        """
        path, filename = os.path.split(self.name)

        path = os.path.join(path, 'thumbnails')
        filename_parts = os.path.splitext(filename)
        # Include the original extension to keep the relationship between image and thumbnail unique
        filename = '{}-{}.png'.format(filename_parts[0], filename_parts[1][1:])

        return os.path.join(path, filename)

    def get_thumbnail_url(self):
        """
        Returns the (absolute) URL for the image's thumbnail version.
        """
        return urljoin(settings.MEDIA_URL, filepath_to_uri(self.get_thumbnail_path()))


class ThumbnailImageField(ImageField):
    """
    Custom variant of ImageField which uses ThumbnailImageFieldFile for its instances.
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
