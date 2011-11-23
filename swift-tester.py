#! /usr/bin/env python

# Author: Marcelo Martins
# Date: 2011-01-20
# Last Update: 2011-06-11 
#
# Info: Just a simple QA test on the CLI for CF testing
#
#


import os, sys, time, tempfile, cloudfiles, logging, urllib2, mimetypes, socket, hashlib
from optparse import OptionParser
from urlparse import urlparse, urlunparse
from xmlrpclib import ServerProxy, Fault
from time import sleep


# colors
global WARNING 
global ENDC 
WARNING = '\033[1;31m'
ENDC = '\033[0m'




def setup_logging(loglevel):
    logging.basicConfig(format='%(asctime)s %(levelname)5s %(name)7s %(message)s', datefmt='%H:%M:%S', level=loglevel)
    my_logger = logging.getLogger('functester')

    fh = logging.FileHandler("swift-tester.log")
    fh.setLevel(loglevel)
    my_logger.addHandler(fh)

    return my_logger




def create_connection(url,user,apikey,logger): 

    count = 0
    #while ( retry > 0) and (retry < 4) :
    while count < 10:
        try:
            count = 4
            start_time = time.time()
            conn = cloudfiles.get_connection(username=user, api_key=apikey, authurl=url)
            duration = time.time() - start_time
            return conn
        except cloudfiles.errors.AuthenticationFailed: 
            count = 4
            duration = time.time() - start_time
            msg = " Failed Authentication  ( %.4f secs)" % duration
            logger( WARNING + msg + ENDC )
            sys.exit(1)
        except cloudfiles.errors.AuthenticationError: 
            count = 4
            duration = time.time() - start_time
            msg = " Authentication Error ( %.4f secs)" % duration
            logger( WARNING + msg + ENDC )
            sys.exit(1)
        except socket.sslerror:
            count = count + 1
            duration = time.time() - start_time
            msg = " Authentication Timed out ... retrying in 5secs ( %.4f secs)" % duration
            logger( WARNING + msg + ENDC )
            time.sleep(3)
            continue 
        except:     
            count = 4
            duration = time.time() - start_time
            msg = " Authentication Issues: %s - %s  ( %.4f secs)" % (sys.exc_type,sys.exc_value,duration)
            raise Exception( WARNING + msg + ENDC )
            #logger( WARNING + msg + ENDC )
            sys.exit(1)

    if count > 0 and count <= 3:
        logger( " Authentication time : %.4f secs, retries : %s " % (duration,count) )
    else:
        logger( " Authentication time : %.4f secs " % duration )




def container_operations (conn, logger, new_containers):

    # First perform some operations on existing data on account connection
    # before making any changes to the account
    try:
        start_time = time.time()
        account_info = conn.get_info()
        duration = time.time() - start_time
        logger( " Containers: %s, Usage: %s bytes " % account_info + ", Retrieval Time: %.4f " % duration)
    except:
        raise Exception( 'Unable to get connection info ')



    try:
        start_time = time.time()
        containers_list = conn.list_containers()
        duration = time.time() - start_time
        logger( " Listing all containers : %.4f secs" % duration )
    except:
        raise Exception( 'Unable to list just containers' )



    try:
        start_time = time.time()
        all_containers_info = conn.list_containers_info()
        duration = time.time() - start_time
        logger( " Listing all container\'s info : %.4f secs" % duration )
    except:
        raise Exception( 'Unable to get all conatiner\'s info'  )



    for name in new_containers:
        try:
            new_container_list = []
            start_time = time.time()
            new_container_list.append( conn.create_container(name) )
            duration = time.time() - start_time
            logger(" Created %d container(s) in : %.4f secs" % (len(new_containers), duration) ) 
        except: 
            duration = 0.0
            logger(" Container creation - Exception Occurred : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)

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

        try:
            start_time = time.time()
            conn[cont.name].list_objects_info()
            duration = time.time() - start_time
            logger(" Container All Objs Information in %.4f secs " % (duration,))
        except:
            duration = 0.0
            logger(" Container All Objs Info - Exception Occurred : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)
    
    


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
    download = True
    current_path = os.path.abspath(sys.path[0]) + "/" 
    tmp_folder = current_path + '/objects' 


    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/24kb.jpg
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/5mb.dmg
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/14mb.dmg
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/28mb.iso
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/56mb.bin
    # http://c0181665.cdn1.cloudfiles.rackspacecloud.com/100mb.iso

    urls = ['http://c0181665.cdn1.cloudfiles.rackspacecloud.com/24kb.jpg',
            'http://c0181665.cdn1.cloudfiles.rackspacecloud.com/5mb.dmg',
            'http://c0181665.cdn1.cloudfiles.rackspacecloud.com/14mb.dmg']
##            'http://c0181665.cdn1.cloudfiles.rackspacecloud.com/28mb.iso']

    #print (" current_path :  %s" % current_path ) 
    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)
    
    for url in urls:
        ofile = tmp_folder + '/' + os.path.basename(url) + ".data" 
        if os.path.isfile(ofile) and os.path.exists(ofile):
            fullpath_files.append(ofile)
            download = False 
        else:
            try:
                urlsh = urllib2.urlopen(url)
                output = open(ofile,'wb')
                output.write(urlsh.read())
                output.close()
                fullpath_files.append(ofile)
                download = True
            except:
                raise Exception ("Error: %s  --  %s" % (sys.exc_type, sys.exc_value) )
    
    if download:
        logger(" Downloaded %s test file(s) successfuly " % len(urls) )
    else:
        logger(" All %s test file(s) already locally available " % len(urls) )


    return fullpath_files



def  cdn_operations(conn, logger, new_containers, tmp_files):

    # Let's mark just one container public
    start_time = time.time()    
    #if not new_containers[0].is_public():
    new_containers[0].make_public()

    duration = time.time() - start_time
    logger(" Set " + str(new_containers[0]) + " public in %.4f secs " % duration )

    cont_name = new_containers[0].name
    cdn_uri = conn[cont_name].public_uri()
    cdn_ssl_uri = conn[cont_name].public_ssl_uri()
    #logger("\t CDN : %s " % cont_name )
    #logger("\t CDN : %s " % cdn_uri )
    #logger("\t CDN-SSL : %s " % cdn_ssl_uri )

    time.sleep(2)
    for fname in tmp_files:
        cdn_url = cdn_uri + "/" + os.path.basename(fname)
        cdn_ssl_url = cdn_ssl_uri + "/" + os.path.basename(fname)
        try:
            start_time = time.time()
            urlsh = urllib2.urlopen(cdn_url)
            contents = urlsh.read() 
            urlsh.close()
            duration = time.time() - start_time
            logger("\t CDN url fetched in %.4f secs ( %s )" % (duration,cdn_url) )
        except:
            logger(" CDN fetch exception : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)

        try:
            start_time = time.time()
            urlsh = urllib2.urlopen(cdn_ssl_url)
            contents = urlsh.read() 
            urlsh.close()
            duration = time.time() - start_time
            logger("\t CDN ssl url fetched in %.4f secs ( %s )" % (duration,cdn_ssl_url) )
        except:
            logger(" CDN ssl fetch exception : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)
        
        try:
            start_time = time.time()
            new_containers[0].log_retention(True)
            logr = new_containers[0].cdn_log_retention
            cdnttl = new_containers[0].cdn_ttl
            new_containers[0].log_retention(False)
            duration = time.time() - start_time
            logger("\t CDN container (log retention = %s, cdnttl = %s) metadata in : %.4f secs" % (logr,cdnttl,duration,) )
        except:
            duration = 0.0
            logger(" Retrieving Container metadata - Exception Occurred : %s, %s " % (sys.exc_type, sys.exc_value) )
            sys.exit(1)
        

    cdnttl = 3600
    if new_containers[0].is_public():
        start_time = time.time()
        new_containers[0].make_public(cdnttl)
        duration = time.time() - start_time    
        logger(" CDN TTL changed to %s in %.4f secs" % (cdnttl,duration) )


    #if conn.list_public_containers():
    try:
        start_time = time.time()
        contents = conn.list_public_containers()
        duration = time.time() - start_time
        logger(" CDN Public Container List in %.4f secs " % (duration,) )
    except:
        logger(" CDN Public Container List exception : %s, %s " % (sys.exc_type, sys.exc_value) )
        sys.exit(1)


    if new_containers[0].is_public():
        start_time = time.time()
        new_containers[0].make_private()
        duration = time.time() - start_time
        logger(" CDN privitized in %.4f secs" % duration )



# Check the Openstack Swift URL 
# Right now really just checks the protocol 
def check_os_swift_authurl(authurl):

    url_components = urlparse(authurl)
    if url_components.scheme == 'http':
        return 0

    elif url_components.scheme == 'https':
        return 0
    else:
        print "\n\t WARNING: The Auth URL protocol provided seems invalid "
        print "\t\t  Please use http or https \n"
        return 1


def main():

    # create command line option parser
    #parser = OptionParser("%prog [options] " + __doc__.rstrip())
    parser = OptionParser(add_help_option=False)

    # configure command line options
    parser.add_option("-h", "--help", action="help")
    parser.add_option("-r", "--region", action="store", type="string", dest="region", help="\t Defines proper CloudFiles Auth URL (us or uk)")
    parser.add_option("-l", "--log-level", action="store", type="int", dest="loglevel", default=1, help="\t Log Level: 1=info (default), 2=error, 3=debug")
    parser.add_option("-i", "--iterations", action="store", type="int", dest="iterations", help="\t Number of test iterations to run")
    parser.add_option("-a", "--authurl", action="store", type="string", dest="authurl", help="\t Auth URL for Openstack-Swift")
    parser.add_option("-u", "--user", action="store", type="string", dest="user", help="\t CloudFiles account username")
    parser.add_option("-k", "--key", action="store", type="string", dest="apikey", help="\t CloudFiles account api key")

    # parse command line options
    (options, args) = parser.parse_args()

    if len(sys.argv) <= 1 :
        parser.print_help()
        sys.exit()

    if options.iterations <= 0 :
        options.iterations = 1

    # Check that user/pass have been provided
    if None in (options.user, options.apikey):
        print "\n\t WARNING: username & password MUST be provided "
        print "\t Run swift-tester.py --help for more details \n"
        sys.exit(1)

    # Check that either -r or -a is provided
    if options.authurl is None and options.region is None:
        print "\n\t WARNING: -r or -a flag MUST be provided "
        print "\t Run swift-tester.py --help for more details \n"
        sys.exit(1)

   
    if options.authurl == None: 
        # If the above is true then "-r" option needs to be used
        # Picking auth url according to region chosen
        if options.region != None:
            if options.region.lower() == 'us':
                authurl="https://auth.api.rackspacecloud.com/auth"
            elif options.region.lower() == 'uk':
                authurl="https://lon.auth.api.rackspacecloud.com/auth"
            else:
                print "\n\t " + WARNING + "Error:" + ENDC + " Region MUST be either US or UK"
                print "\n\t Run swift-tester.py --help for more details \n"
                sys.exit(1)
#        else:
#            print "\n\t WARNING: -r or -a flag MUST be provided .. Not both \n"
#            print "\n\t Run swift-tester.py --help for more details \n"
#            return 1
#            sys.exit()

    else:
        if options.region != None:
            print "\n\t WARNING: you cannot specify -r and -a at the same time "
            print "\t Run swift-tester.py --help for more details \n"
            sys.exit(1)
        else:
            authurl = options.authurl.lower() 
            status = check_os_swift_authurl(authurl)
            if status == 1:
                sys.exit(status)


    
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


    # Setup a random string container to use
    # for now uses only one container 
    container =  "basket_"+hashlib.md5(os.urandom(2048)).hexdigest() 
    containers = []
    containers.append(container)

    
    # Start iterations
    runs = 1

    localtime = time.asctime( time.localtime(time.time()) )

    print("\n")
    my_logger(" ***** Began on: %s ***** " % localtime)
    my_logger(" ***** Python-Cloudfiles Ver. %s " % cloudfiles.__version__ )
    my_logger(" ")

    while (runs <= options.iterations):

        my_logger(" ***** Starting Iteration # %d ***** " % runs )

        conn = create_connection (authurl, options.user, options.apikey, my_logger)
        containers_list = container_operations (conn,my_logger, containers)
        
        # get files to be used for object operations
        #current_path = os.path.abspath(sys.path[0]) + "/" + os.path.basename(sys.argv[0])
        tmp_folder = os.path.abspath(sys.path[0]) + "/" + os.path.basename(sys.argv[0]) + '/objects' 
        tmp_files = create_test_files(my_logger, tmp_folder) 

        object_operations(conn, my_logger, containers_list, tmp_files)
        
        # Only run CDN tests if running against CloudFiles environment
        if options.region != None:
            cdn_operations(conn, my_logger, containers_list, tmp_files)

        cleanup_containers (conn,my_logger, containers_list)
    
        runs = runs + 1
        print ("\n")

    print ("\n")
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)


