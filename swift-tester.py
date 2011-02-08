#! /usr/bin/env python

# Author: Marcelo Martins
# Date: 01-20-2011
#
# Info: Just a simple QA test on the CLI for CF testing
#
#


import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore",category=DeprecationWarning)
    import md5

import os, sys, time, urllib, tempfile, cloudfiles, logging, urllib2, mimetypes
from optparse import OptionParser
from xmlrpclib import ServerProxy, Fault
from time import sleep
#from urllib2 import urlopen, Request


# colors
global WARNING 
global ENDC 
WARNING = '\033[1;31m'
ENDC = '\033[0m'





def setup_logging(loglevel):
    logging.basicConfig(format='%(asctime)s %(levelname)5s %(name)7s %(message)s', datefmt='%H:%M:%S', level=loglevel)
    my_logger = logging.getLogger('QAtester')
    return my_logger


def md5_from_filename(fname):
    f = open(fname, "rb")
    contents = f.read()
    f.close()
    return md5.new(contents).hexdigest()


def create_connection(url,user,apikey,logger): 

    try:
        start_time = time.time()
        conn = cloudfiles.get_connection(username=user, api_key=apikey, authurl=url)
        duration = time.time() - start_time
    except cloudfiles.errors.AuthenticationFailed: 
        duration = time.time() - start_time
        print ( " --> %s , %s " % (sys.exc_type, sys.exc_value) )
        msg = "Failed Authentication  ( %.4f secs)" % duration
        raise Exception( WARNING + msg + ENDC )
    
    logger( " Authentication time : %.4f secs" % duration )

    return conn



def container_operations (conn, logger, new_containers):


    # First perform some operations on existing data on account connection
    # before making any changes to the account
    try:
        start_time = time.time()
        account_info = conn.get_info()
        duration = time.time() - start_time
    except:
        raise Exception( 'Unable to get connection info ')

    logger( " Containers: %s, Usage: %s bytes " % account_info + ", Retrieval Time: %.4f " % duration)


    try:
        start_time = time.time()
        containers_list = conn.list_containers()
        duration = time.time() - start_time
    except:
        raise Exception( 'Unable to list just containers' )

    logger( " Listing all containers : %.4f " % duration )


    try:
        start_time = time.time()
        all_containers_info = conn.list_containers_info()
        duration = time.time() - start_time
    except:
        raise Exception( 'Unable to get all conatiner\'s info'  )

    logger( " Listing all container\'s info : %.4f " % duration )



    for name in new_containers:
        try:
            new_container_list = []
            start_time = time.time()
            new_container_list.append( conn.create_container(name) )
            duration = time.time() - start_time
        except: 
            duration = 0.0
            logger(" Container creation - Exception Occurred : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)

    logger(" Created %d container(s) in : %.4f secs" % (len(new_containers), duration) ) 

    return new_container_list



def object_operations(conn, logger, new_containers, tmp_files):

    obj = None    
    start_time = time.time()

    for cont in new_containers:
        for fname in tmp_files:
            try:
                mtype,enctype = mimetypes.guess_type(fname)
                obj = cont.create_object(os.path.basename(fname))
                obj.content_type = str(mtype)
                obj.load_from_filename(fname)
            except:
                duration = 0.0
                logger(" Object creation exception : %s, %s " % (sys.exc_type, sys.exc_value) )
                sys.exit(1) 

    duration = time.time() - start_time
    logger(" Uploaded %s file(s) in %s container(s) in : %.4f secs " % (len(tmp_files), len(new_containers), duration) )

    
    


def cleanup_containers(conn, logger, new_containers):

    for cname in new_containers:
        for oname in cname.list_objects():
            try:
                cname.delete_object(oname)
            except:
                logger(" Object deletion - Exception Occurred : %s, %s " % (sys.exc_type, sys.exc_value) )
                sys.exit(1)

        try:
            start_time = time.time()
            conn.delete_container(cname)
            duration = time.time() - start_time
        except:
            duration = 0.0
            logger(" Container deletion - Exception Occurred : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)

    logger(" Deleted %d container(s) in : %.4f secs" % (len(new_containers), duration) )
    
    


def create_test_files(logger, tmp_folder):

    fullpath_files = []
    current_path = os.path.abspath(sys.path[0]) + "/" 
    tmp_folder = current_path + '/objects' 

    #print (" current_path :  %s" % current_path ) 
    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)

    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/24kb.jpg
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/5mb.dmg
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/14mb.dmg
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/28mb.iso
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/56mb.bin
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/100mb.iso

    urls = ['http://c0181665.cdn1.cloudfiles.rackspacecloud.com/24kb.jpg',
            'http://c0181665.cdn1.cloudfiles.rackspacecloud.com/5mb.dmg']
##            'http://c0181665.cdn1.cloudfiles.rackspacecloud.com/14mb.dmg',
##            'http://c0181665.cdn1.cloudfiles.rackspacecloud.com/28mb.iso']

    for url in urls:

        try:
            urlsh = urllib2.urlopen(url)
            ofile = tmp_folder + '/' + os.path.basename(url)
            fullpath_files.append(ofile)
            output = open(ofile,'wb')
            output.write(urlsh.read())
            output.close()
        except:
            raise Exception ("Error: %s  --  %s" % (sys.exc_type, sys.exc_value) )

    logger(" Created %s temporary file(s) successfuly " % len(urls) )

    return fullpath_files



def  cdn_operations(conn, logger, new_containers, tmp_files):


    # Let's mark just one container public

    
    start_time = time.time()    
    #if not new_containers[0].is_public():
    new_containers[0].make_public()

    duration = time.time() - start_time
    logger(" Set " + str(new_containers[0]) + " public in %.4f secs " % duration )

    cdn_uri = new_containers[0].public_uri()
    time.sleep(2)
    for fname in tmp_files:
        cdn_url = cdn_uri + "/" + os.path.basename(fname)
        try:
            start_time = time.time()
            urlsh = urllib2.urlopen(cdn_url)
            contents = urlsh.read() 
            urlsh.close()
            duration = time.time() - start_time
        except:
            logger(" CDN fetch exception : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)
        
        logger("\t CDN url fetched in %.4f secs ( %s )" % (duration,cdn_url) )
        

    cdnttl = 7200
    if new_containers[0].is_public():
        start_time = time.time()
        new_containers[0].make_public(cdnttl)
        duration = time.time() - start_time    
        
    logger(" CDN TTL changed to %s in %.4f secs" % (cdnttl,duration) )



    if new_containers[0].is_public():
        start_time = time.time()
        new_containers[0].make_private()
        duration = time.time() - start_time

    logger(" CDN privitized in %s secs" % duration )



def main():

    # create command line option parser
    #parser = OptionParser("%prog [options] " + __doc__.rstrip())
    parser = OptionParser(add_help_option=False)

    # configure command line options
    parser.add_option("-h", "--help", action="help")
    parser.add_option("-r", "--region", action="store", type="string", dest="region", help="\t\t Defines proper Auth URL (us or uk)")
    parser.add_option("-l", "--log-level", action="store", type="int", dest="loglevel", default=1, help="\t\t Log Level: 1=info (default), 2=error, 3=debug")
    parser.add_option("-i", "--iterations", action="store", type="int", dest="iterations", help="\t\t Number of test iterations to run")
    parser.add_option("-u", "--user", action="store", type="string", dest="user", help="\t\t CloudFiles account username")
    parser.add_option("-k", "--key", action="store", type="string", dest="apikey", help="\t\t CloudFiles account api key")

    # parse command line options
    (options, args) = parser.parse_args()
    #print options
    #print args

    if options.iterations <= 0 :
        print "\n\t " + WARNING + "Error:" + ENDC + " Iterations must be greater or equal to 1 \n"
        return 1
        sys.exit()

    # Picking auth url according to region chosen
    if options.region.lower() == 'us':
        #print "USA region"
        authurl="https://api.mosso.com/auth"
    elif options.region.lower() == 'uk':
        #print "GB region"
        authurl="https://lon.auth.api.rackspacecloud.com/auth"
    else:
        print "\n\t " + WARNING + "Error:" + ENDC + " Region MUST be either US or UK"
        return 1 
        sys.exit()

    
    # Setting up the log level
    if options.loglevel == 1:
        # logging.INFO 
        loglevel=20
    elif options.loglevel == 2:
        # logging.ERROR
        loglevel=40
    elif options.loglevel == 3:
        # logging.DEBUG
        loglevel=10
    else:
        # logging.INFO
        loglevel=20
        #print "\n\t " + WARNING + "Error:" + ENDC + " Please choose a proper log level"
        #sys.exit(1)

    # The --user and --apikey options are required 
    if options.user is None :
        parser.error("-u, --user is required")

    if options.apikey is None :
        parser.error("-k, --apikey is required")


    app_logger = setup_logging(loglevel)
    if app_logger.getEffectiveLevel() == 20:
        my_logger = app_logger.info

    if app_logger.getEffectiveLevel() == 40:
        my_logger = app_logger.error

    if app_logger.getEffectiveLevel() == 10:
        my_logger = app_logger.debug


    # containers to use
    containers = ['basket_one']

    
    # Start iterations
    runs = 1
    while (runs <= options.iterations):

        print ("")
        my_logger(" ***** Starting Iteration # %d ***** " % runs )

        conn = create_connection (authurl, options.user, options.apikey, my_logger)
        containers_list = container_operations (conn,my_logger, containers)
        
        # get files to be used for object operations
        #current_path = os.path.abspath(sys.path[0]) + "/" + os.path.basename(sys.argv[0])
        tmp_folder = os.path.abspath(sys.path[0]) + "/" + os.path.basename(sys.argv[0]) + '/objects' 
        tmp_files = create_test_files(my_logger, tmp_folder) 

        object_operations(conn, my_logger, containers_list, tmp_files)
        cdn_operations(conn, my_logger, containers_list, tmp_files)
        cleanup_containers (conn,my_logger, containers_list)
    
        runs = runs + 1

    print ("\n")
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)

