/* decompress a memory area containing a jpeg to an RGB buffer
 *
 * this is designed to be called from Python with ctypes 
 *
 * on linux, compile with
 
  	gcc -c -Wall -shared -fPIC dejpeg.c 
 	ld -shared dejpeg.o -o dejpeg.so -ljpeg

 * it needs the jpeg headers to compile --- if they are not installed, get
 * them with
 *
 * 	sudo apt-get install libjpeg62-dev
 */

/*
 * 3/5/11
 * 	- hacked from libvips sources
 */

/*
#define DEBUG
 */

#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>

#include <jpeglib.h>
#include <jerror.h>

/* A decompressed image.
 */
typedef struct _Image {
	int width;
	int height;
	void *pixels;
} Image;

/* Called from Python on finalize.
 */
void
image_free( Image *image )
{
	if( image->pixels )
		free( image->pixels );
}

/* Define a new error handler for when we bomb out.
 */
typedef struct {
	/* Public fields.
	 */
	struct jpeg_error_mgr pub;

	/* Private stuff for us.
	 */
	jmp_buf jmp;		/* longjmp() here to get back to VIPS */
	FILE *fp;		/* fclose() if non-NULL */
} ErrorManager;

/* New output message method - send to VIPS.
 */
static void
new_output_message( j_common_ptr cinfo )
{
#ifdef DEBUG
	char buffer[JMSG_LENGTH_MAX];

	(*cinfo->err->format_message)( cinfo, buffer );
	printf( "im_jpeg2vips: new_output_message: \"%s\"\n", buffer );
#endif /*DEBUG*/
}

/* New error_exit handler.
 */
static void 
new_error_exit( j_common_ptr cinfo )
{
	ErrorManager *eman = (ErrorManager *) cinfo->err;

#ifdef DEBUG
	printf( "im_jpeg2vips: new_error_exit\n" );
#endif /*DEBUG*/

	/* Close the fp if necessary.
	 */
	if( eman->fp ) {
		(void) fclose( eman->fp );
		eman->fp = NULL;
	}

	/* Send the error message to VIPS. This method is overridden above.
	 */
	(*cinfo->err->output_message)( cinfo );

	/* Jump back.
	 */
	longjmp( eman->jmp, 1 );
}

/* Just like the above, but we read from a memory buffer.
 */
typedef struct {
	/* Public jpeg fields.
	 */
	struct jpeg_source_mgr pub;

	/* Private stuff during read.
	 */
	int start_of_file;	/* have we gotten any data yet? */
	JOCTET *buf;
	size_t len;
} InputBuffer;

/*
 * Initialize source --- called by jpeg_read_header
 * before any data is actually read.
 */

static void
init_source (j_decompress_ptr cinfo)
{
  InputBuffer *src = (InputBuffer *) cinfo->src;

  /* We reset the empty-input-file flag for each image,
   * but we don't clear the input buffer.
   * This is correct behavior for reading a series of images from one source.
   */
  src->start_of_file = 1;
}

/*
 * Fill the input buffer --- called whenever buffer is emptied.
 *
 * In typical applications, this should read fresh data into the buffer
 * (ignoring the current state of next_input_byte & bytes_in_buffer),
 * reset the pointer & count to the start of the buffer, and return TRUE
 * indicating that the buffer has been reloaded.  It is not necessary to
 * fill the buffer entirely, only to obtain at least one more byte.
 *
 * There is no such thing as an EOF return.  If the end of the file has been
 * reached, the routine has a choice of ERREXIT() or inserting fake data into
 * the buffer.  In most cases, generating a warning message and inserting a
 * fake EOI marker is the best course of action --- this will allow the
 * decompressor to output however much of the image is there.  However,
 * the resulting error message is misleading if the real problem is an empty
 * input file, so we handle that case specially.
 *
 * In applications that need to be able to suspend compression due to input
 * not being available yet, a FALSE return indicates that no more data can be
 * obtained right now, but more may be forthcoming later.  In this situation,
 * the decompressor will return to its caller (with an indication of the
 * number of scanlines it has read, if any).  The application should resume
 * decompression after it has loaded more data into the input buffer.  Note
 * that there are substantial restrictions on the use of suspension --- see
 * the documentation.
 *
 * When suspending, the decompressor will back up to a convenient restart point
 * (typically the start of the current MCU). next_input_byte & bytes_in_buffer
 * indicate where the restart point will be if the current call returns FALSE.
 * Data beyond this point must be rescanned after resumption, so move it to
 * the front of the buffer rather than discarding it.
 */

static boolean
fill_input_buffer (j_decompress_ptr cinfo)
{
  InputBuffer *src = (InputBuffer *) cinfo->src;
  size_t nbytes;

  if (src->start_of_file) {
    nbytes = src->len;
  }
  else {
    WARNMS(cinfo, JWRN_JPEG_EOF);
    /* Insert a fake EOI marker */
    src->buf[0] = (JOCTET) 0xFF;
    src->buf[1] = (JOCTET) JPEG_EOI;
    nbytes = 2;
  }

  src->pub.next_input_byte = src->buf;
  src->pub.bytes_in_buffer = nbytes;
  src->start_of_file = 0;

  return TRUE;
}

/*
 * Skip data --- used to skip over a potentially large amount of
 * uninteresting data (such as an APPn marker).
 *
 * Writers of suspendable-input applications must note that skip_input_data
 * is not granted the right to give a suspension return.  If the skip extends
 * beyond the data currently in the buffer, the buffer can be marked empty so
 * that the next read will cause a fill_input_buffer call that can suspend.
 * Arranging for additional bytes to be discarded before reloading the input
 * buffer is the application writer's problem.
 */

static void
skip_input_data (j_decompress_ptr cinfo, long num_bytes)
{
  InputBuffer *src = (InputBuffer *) cinfo->src;

  /* Just skip fwd.
   */
  if (num_bytes > 0) {
    src->pub.next_input_byte += (size_t) num_bytes;
    src->pub.bytes_in_buffer -= (size_t) num_bytes;
  }
}

/*
 * An additional method that can be provided by data source modules is the
 * resync_to_restart method for error recovery in the presence of RST markers.
 * For the moment, this source module just uses the default resync method
 * provided by the JPEG library.  That method assumes that no backtracking
 * is possible.
 */

/*
 * Terminate source --- called by jpeg_finish_decompress
 * after all data has been read.  Often a no-op.
 *
 * NB: *not* called by jpeg_abort or jpeg_destroy; surrounding
 * application must deal with any cleanup that should happen even
 * for error exit.
 */

static void
term_source (j_decompress_ptr cinfo)
{
  /* no work necessary here */
}

/*
 * Prepare for input from a memory buffer. The caller needs to free the
 * buffer after decompress is done, we don't take ownership.
 */

static void
buf_source (j_decompress_ptr cinfo, void *buf, size_t len)
{
  InputBuffer *src;

  /* The source object and input buffer are made permanent so that a series
   * of JPEG images can be read from the same file by calling jpeg_stdio_src
   * only before the first one.  (If we discarded the buffer at the end of
   * one image, we'd likely lose the start of the next one.)
   * This makes it unsafe to use this manager and a different source
   * manager serially with the same JPEG object.  Caveat programmer.
   */
  if (cinfo->src == NULL) {	/* first time for this JPEG object? */
    cinfo->src = (struct jpeg_source_mgr *)
      (*cinfo->mem->alloc_small) ((j_common_ptr) cinfo, JPOOL_PERMANENT,
				  sizeof(InputBuffer));
    src = (InputBuffer *) cinfo->src;
    src->buf = buf;
    src->len = len;
  }

  src = (InputBuffer *) cinfo->src;
  src->pub.init_source = init_source;
  src->pub.fill_input_buffer = fill_input_buffer;
  src->pub.skip_input_data = skip_input_data;
  src->pub.resync_to_restart = jpeg_resync_to_restart; /* use default method */
  src->pub.term_source = term_source;
  src->pub.bytes_in_buffer = 0; /* forces fill_input_buffer on first read */
  src->pub.next_input_byte = NULL; /* until buffer loaded */
}

/**
 * im_bufjpeg2vips:
 * @buf: memory area to load
 * @len: size of memory area
 * @out: image to write
 * @header_only: set to just read the header
 *
 * Read a JPEG-formatted memory block into a VIPS image. It can read most 
 * 8-bit JPEG images, including CMYK and YCbCr.
 *
 * This function is handy for processing JPEG image thumbnails.
 *
 * See also: #VipsFormat, im_jpeg2vips().
 *
 * Returns: 0 on success, -1 on error.
 */
int
decompress( void *buf, size_t len, Image *out )
{
	struct jpeg_decompress_struct cinfo;
	ErrorManager eman;
	int y;

	out->width = -1;
	out->height = -1;
	out->pixels = NULL;

	/* Make jpeg dcompression object.
 	 */
	cinfo.err = jpeg_std_error( &eman.pub );
	eman.pub.error_exit = new_error_exit;
	eman.pub.output_message = new_output_message;
	eman.fp = NULL;
	if( setjmp( eman.jmp ) ) {
		/* Here for longjmp() from new_error_exit().
		 */
		jpeg_destroy_decompress( &cinfo );
		image_free( out );

		return( -1 );
	}
	jpeg_create_decompress( &cinfo );

	/* Make input.
	 */
	buf_source( &cinfo, buf, len );

	/* Read JPEG header. libjpeg will set out_color_space sanely for us 
	 * for YUV YCCK etc.
	 */
	jpeg_read_header( &cinfo, TRUE );
	jpeg_calc_output_dimensions( &cinfo );

	if( cinfo.out_color_space != JCS_RGB ) {
		/* We should use the libjpeg error reporter to fix this leak.
		 */
		printf( "decompress: RGB jpeg only\n" );

		return( -1 );
	}

	out->width = cinfo.output_width;
	out->height = cinfo.output_height;
	if( !(out->pixels = malloc( out->width * out->height * 3 )) ) {
		/* We should use the libjpeg error reporter to fix this leak.
		 */
		image_free( out );
		return( -1 );
	}

	/* Start up decompressor.
	 */
	jpeg_start_decompress( &cinfo );

	/* Process image.
	 */
	for( y = 0; y < out->height; y++ ) {
		char *p;

		p = ((char *) out->pixels) + y * out->width * 3;

		/* We set an error handler that longjmps() out, so I don't
		 * think this can fail.
		 */
		jpeg_read_scanlines( &cinfo, (JSAMPARRAY) &p, 1 );
	}

	/* Stop decompressor.
	 */
	jpeg_finish_decompress( &cinfo );

	/* Close and tidy.
	 */
	jpeg_destroy_decompress( &cinfo );

	return( 0 );
}
