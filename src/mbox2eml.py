#!/usr/bin/env python3
#===============================================================================
#   mbox2eml.py     |   version 0.81    |   zlib license    |   2020-02-10
#   James Hendrie   |   hendrie.james@gmail.com
#
#   Script that splits an mbox file into a bunch of eml files.
#===============================================================================
import sys, os
import base64

gOpts = { "verbose" : True }


def print_usage():
    print( "Usage:  mbox2eml.py MBOX_FILE[s] [output_directory]" )


def print_help():
    print("This script will split an mbox format file into a bunch of separate")
    print( "eml format files.  By default, it will also try to guess at the" )
    print( "subject, too, naming the output files as best it can." )

class Email:
    def __init__( self, linesOfText=[] ):
        self.lines = linesOfText
        self.byteString = self.byte_string( self.lines )
        self.subject = self.subject()

    def decode_subject( self, subject ):
        """
        Params
            subject     utf-8 encoded byte object, our subject (text)

        This method does what it can to decode a given subject line, assuming it
        needed decoding in the first place.
        """

        ##  Various different tokens we'll be looking for, to determine the type
        ##  of decoding we'll try
        b = "=?utf-8?b?"
        ab = "?us-ascii?b?"
        q = "=?utf-8?q?"
        aq = "=?us-ascii?q?"

        ##  A common end token, so we only grab what we need
        endTok = bytes( "?=", "utf-8" )

        ##  Subjects encoded in base64
        for bTok in ( '?b?', '?B?' ):
            tok = bytes( bTok, "utf-8" )
            if tok in subject[:20]:
                sub = subject.partition( tok )[2].partition( endTok )[0]
                return( base64.decodebytes( sub ))

        ##  Subjects with wonky-looking 'clear' text encoding
        for qTok in ( '?q?', '?Q?' ):
            tok = bytes( qTok, "utf-8" )
            if tok in subject[:20]:
                sub = subject.partition(tok)[2].partition( endTok )[0].decode()
                return( sub.replace( '_', ' ', -1 ))

    def byte_string( self, lines ):
        """
        Params:
            lines   A list of byte objects (utf-8 encoded lines of text)

        This method combines all of our lines of text into a single line, then
        returns it.
        """

        s = bytes( "", "utf-8" )
        for bo in lines:
            s += bo

        return( s )


    def subject( self ):
        """
        Attempts to fetch the subject of the email.  If nothing can be found,
        some standin text is provided instead.
        """

        ##  A long, encoded string of all the email data
        email = self.byteString

        ##  Find the subject line, then find where the line ends and consider
        ##  that to be the subject.  Multi-line subjects can get fucked, lol
        idx = email.find( bytes( "Subject: ", "utf-8" ))
        end = email.find( bytes( "\n", "utf-8"), idx )
        subject = email[ idx : end ]

        ##  If we're left with nothing after stripping whitespace, we'll assume
        ##  we've hit a dud and keep movin' on down
        while subject.strip() == "":
            start = end
            idx = email.find( bytes( "Subject: ", "utf-8" ), start )
            end = email.find( bytes( "\n", "utf-8"), idx )
            subject = email[ idx : end ]

        ##  If the sender has decided to be a prick and encode the subject in
        ##  some base-64 bullshit, we'll attempt to determine as much here and
        ##  try to decode it
        annoying = "=?utf-8?"
        aAnnoying = "=?us-ascii?"
        for a in ( annoying, annoying.upper(), aAnnoying, aAnnoying.upper() ):
            if bytes( a, "utf-8" ) in subject:
                subject = self.decode_subject( subject )
                break

        if type( subject ) == type( bytes() ):
            try:
                subStr = subject.decode()
            except UnicodeDecodeError:
                subStr = "_INVALID-SUBJECT_"
        else:
            subStr = subject

        ##  Finally, we get our usable 'subject string' by removing certain
        ##  bits of it, making it slightly more unix-friendly
        if subStr != "" and subStr != None:
            final = subStr.replace( "Subject: ", '', -1 )
            final = final.replace( '/', '', -1 )
            return( final )

        ##  If all else fails, we return this beauty
        return( "_NO-SUBJECT_" )


class MBox:

    def __init__( self, mboxPath = "" ):
        self.mbox = mboxPath
        self.emails = []

    def name( self ):
        """
        Returns the name (basename minus extension) of the mbox in question
        """

        return( self.mbox[ : os.path.basename( self.mbox ).rfind( '.') ] )

    def emails_from_path( self, mboxPath ):
        """
        Params:
            mboxPath    Path to the mbox file

        Here we read from the actual mbox file, extracting each individual
        email's lines and saving them (as Email objects) to the self.emails
        list.
        """

        ##  Open the mbox file and read all of its lines
        io = open( mboxPath, "rb" )
        lines = io.readlines()
        io.close()

        ##  Keep a running tally of where all our eml files begin by looking
        ##  for a specific phrase
        starts = []
        idx = 0
        while idx < len( lines ):
            if bytes( "Delivered-To:", "utf-8" ) in lines[ idx ]:
                starts.append( idx - 1 )
            idx += 1


        ##  Go through the lines from 'start' to 'start', recording everything
        ##  between as the email itself
        count = 0
        num = len( starts )
        pad = len( str( num))
        for s in starts:
            idx = starts.index( s )
            if gOpts[ "verbose" ]:
                count += 1
                print( "Extracting %0*d / %0*d\tfrom '%s'"
                        % ( pad, count, pad, num, mboxPath))

            if idx < len( starts ) - 1:
                self.emails.append( Email( lines[ s : starts[ idx + 1 ] ] ))
            else:
                self.emails.append( Email( lines[ s : ] ))


    def split( self, outputDir ):
        """
        Params:
            outputDir   Where we're sticking our eml files

        Call another method to do the actual email extraction, then put together
        a filename and write all of the files.
        """


        ##  Extract the emails from the mbox
        self.emails_from_path( self.mbox )

        ##  Directory stuff, keep track of where we are then switch to the
        ##  output directory
        bookmark = os.getcwd()
        os.chdir( outputDir )

        ##  Start getting filenames for the files we'll write, then write them
        numEmails = len( self.emails )
        pad = len( str( numEmails ))
        count = 1
        mboxName = self.name()
        for e in self.emails:

            ##  If we're verbose (default), tell the user's what's going on
            if gOpts[ "verbose" ]:
                print( "Writing %0*d / %0*d\tinto directory '%s'" %
                        ( pad, count, pad, numEmails, outputDir ))

            ##  Put together our filename, write the file
            fileName = "%s-%0*d-%s.eml" % ( mboxName, pad, count, e.subject )
            of = open( fileName, 'wb' )
            of.write( e.byteString )
            of.close()

            count += 1

        ##  Go back to where we started
        os.chdir( bookmark )


def new_dir( path ):
    try:
        os.mkdir( path )
        return( True )
    except ( OSError, PermissionError ):
        return( False )


def dir_stuff( path ):
    """
    If the path doesn't exist, create it or report an error.
    """
    if not os.path.exists( path ):
        if not new_dir( path ):
            print( "Uh-oh!" )
            sys.exit( 1 )


def process_mbox_file( mboxFile, outputDir ):
    """
    Params::
        mboxFile    Path to our mbox file
        outputDir   Path to our output directory

        First we make sure the output dir is workable, then create an mbox
        object, which will then split the given mbox file (path) into a bunch
        of eml files.
    """
    dir_stuff( outputDir )
    mbox = MBox( mboxFile )
    mbox.split( outputDir )


def main():
    ##  See if they're using the correct number of arguments
    if len( sys.argv ) < 2:
        print_usage()
        sys.exit( 1 )

    if len( sys.argv ) < 3:

        ##  Do they want help?
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            print_usage()
            print( "" )
            print_help()
            sys.exit( 0 )

        ##  Process our single mbox file
        d = "%s.d" % sys.argv[1]
        process_mbox_file( sys.argv[1], d )

    else:
        ##  Check the last argument, see if it's an output directory
        if os.path.isdir( sys.argv[-1] ):
            d = sys.argv[-1]
            for arg in sys.argv[1:-1]:
                process_mbox_file( arg, d )

        ##  Otherwise, just do the .d thing for all the mbox files' dirs
        else:
            for arg in sys.argv[1:]:
                d = "%s.d" % arg
                process_mbox_file( arg, d )
            

    print( "\nAll done!" )

if __name__ == "__main__":
    main()
