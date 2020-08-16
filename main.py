import jpeg_parser

with open("example.jpg", "rb") as jpeg_file:
    jpeg_parser.read_jfif_header(jpeg_file)
    while True:
        marker_position = jpeg_parser.get_next_marker(jpeg_file)
        if marker_position is None:
            break
        print("{}".format(hex(marker_position)))
