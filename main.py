import typing
import struct
from collections import namedtuple
"""
typedef struct _JFIFHeader
{
  BYTE SOI[2];          /* 00h  Start of Image Marker     */
  BYTE APP0[2];         /* 02h  Application Use Marker    */
  BYTE Length[2];       /* 04h  Length of APP0 Field      */
  BYTE Identifier[5];   /* 06h  "JFIF" (zero terminated) Id String */
  BYTE Version[2];      /* 07h  JFIF Format Revision      */
  BYTE Units;           /* 09h  Units used for Resolution */
  BYTE Xdensity[2];     /* 0Ah  Horizontal Resolution     */
  BYTE Ydensity[2];     /* 0Ch  Vertical Resolution       */
  BYTE XThumbnail;      /* 0Eh  Horizontal Pixel Count    */
  BYTE YThumbnail;      /* 0Fh  Vertical Pixel Count      */
} JFIFHEAD;
"""

SOI_EXPECTED = (0xFF, 0xD8)
JFIF_APP0_EXPECTED = (0xFF, 0xE0)

def unpack_from_file(format, file_):
    return struct.unpack(
        format,
        file_.read(struct.calcsize(format))
    )

def one_from_file(format, file_):
    return unpack_from_file(format, file_)[0]

def read_jpeg_header(file_):
    # SOI is the start of image marker and always contains the marker code
    # values FFh D8h.
    assert unpack_from_file("2B", file_) == SOI_EXPECTED

    # APP0 is the Application marker and always contains the marker code values
    # FFh E0h.
    assert unpack_from_file("2B", file_) == JFIF_APP0_EXPECTED  # APP0

    # Length is the size of the JFIF (APP0) marker segment, including the size
    # of the Length field itself and any thumbnail data contained in the APP0
    # segment. Because of this, the value of Length equals
    # 16 + 3 * XThumbnail * YThumbnail.
    length = unpack_from_file("2B", file_)
    # TODO: check the value

    # Identifier contains the values 4Ah 46h 49h 46h 00h (JFIF) and is used to
    # identify the code stream as conforming to the JFIF specification.
    assert one_from_file("5s", file_) == b"JFIF\x00"
    print("JFIF version: {}".format(unpack_from_file("2B", file_)))

    # Units, Xdensity, and Ydensity identify the unit of measurement used to
    # describe the image resolution.
    # Units may be:
    #  - 01h for dots per inch
    #  - 02h for dots per centimeter
    #  - 00h for none (use measurement as pixel aspect ratio).
    units = one_from_file("B", file_)
    print("Units: {}".format(units))

    # Xdensity and Ydensity are the horizontal and vertical resolution of the
    # image data, respectively. If the Units field value is 00h, the Xdensity
    # and Ydensity fields will contain the pixel aspect ratio
    # (Xdensity : Ydensity) rather than the image resolution.
    # Because non-square pixels are discouraged for portability reasons, the
    # Xdensity and Ydensity values normally equal 1 when the Units value is 0.
    x_density = one_from_file("H", file_)
    y_density = one_from_file("H", file_)
    print("x_density: {}, y_density: {}".format(x_density, y_density))

    x_thumbnail = one_from_file("B", file_)
    y_thumbnail = one_from_file("B", file_)
    print("x_thumbnail: {}, y_thumbnail: {}".format(x_thumbnail, y_thumbnail))

    if x_thumbnail * y_thumbnail > 0:
        # (RGB) * k (3 * k bytes) Packed (byte-interleaved) 24-bit RGB values
        # (8 bits per colour channel) for the thumbnail pixels, in the order
        # R0, G0, B0, ... Rk,
        # Gk, Bk, with k = HthumbnailA * VthumbnailA.
        thumbnail_data = file_.read(3 * x_thumbnail * y_thumbnail)
        print("discarding {} bytes of thumbnail data".format(
            len(thumbnail_data)
        ))

def check_if_app0_extension(file_: typing.BinaryIO):
    seek_position = file_.tell()  # save current file position to reset to later

    # Total APP0 field byte count, including the byte count value (2 bytes),
    # but excluding the APP0 marker itself.
    # Shall be equal to the number of bytes of extension_data plus 8.
    lp = one_from_file("H", file_) # total data in extension header
    identifier = one_from_file("5s", file_)
    print(identifier)

DHT_MARKER = 0xC4

# https://en.wikipedia.org/wiki/JPEG#Syntax_and_structure
Marker = namedtuple('Marker', ['short', 'name', 'decoder'])

MARKER_LOOKUP = {
    0xD8: Marker(short="SOI", name="Start Of Image", decoder=None),
    0xC0: Marker(short="SOF0", name="Start Of Frame (baseline DCT)", decoder=None),
    0xC2: Marker(short="SOF2", name="Start Of Frame (progressive DCT)", decoder=None),
    0xC4: Marker(short="DHT", name="Define Huffman Table(s)", decoder=None),
    0xDB: Marker(short="DQT", name="Define Quantization Table(s)", decoder=None),
    0xDD: Marker(short="DRI", name="Define Restart Interval", decoder=None),
    0xDA: Marker(short="SOS", name="Start Of Scan", decoder=None),
    # Restart defined in loop
    # Application-specific defined in loop
    0xFE: Marker(short="COM", name="Comment", decoder=None),
    0xD9: Marker(short="EOI", name="End Of Image", decoder=None)
}

# insert Restart markers
for n in range(8):
    # make 0xDn (n=0..7) for RSTn
    restart_marker_byte = int("D{}".format(n), 16)
    MARKER_LOOKUP[restart_marker_byte] = Marker(
        short="RST{}".format(n),
        name="Restart",
        decoder=None  # ?
    )

# insert App markers
for n in range(8):
    # make 0xEn (n=0..7) for APPn
    app_marker_byte = int("E{}".format(n), 16)
    MARKER_LOOKUP[app_marker_byte] = Marker(
        short="APP{}".format(n),
        name="Application-specific",
        decoder=None  # ?
    )

def get_next_marker(file_):
    """ returns the next marker, with it's index """
    seek_position = file_.tell()
    # ignore byte-stuffed FFs (0xFF, 0x00)
    def find_next_ff():
        byte = file_.read(1)
        while byte != b"\xFF":
            byte = file_.read(1)
            if byte == b"":
                return None  # EOF
        return file_.read(1)  # read marker identifier (or 0x00)

    while True:
        marker_identifier = find_next_ff()
        if marker_identifier is None:
            return None  # EOF
        if marker_identifier != b"\x00":
            break  # not a byte stuffed thing!

    int_marker_id = struct.unpack("B", marker_identifier)[0]

    if int_marker_id in MARKER_LOOKUP:
        found_marker = MARKER_LOOKUP[int_marker_id]
        print("Found marker {}, {}, {}".format(
            hex(int_marker_id),
            found_marker.short,
            found_marker.name
        ))
    else:
        print("Unknown marker {}".format(
            hex(int_marker_id)
        ))

    return file_.tell() - 2  # right before the marker byte


with open("example.jpg", "rb") as jpeg_file:
    read_jpeg_header(jpeg_file)
    while True:
        marker = get_next_marker(jpeg_file)
        if marker is None:
            break