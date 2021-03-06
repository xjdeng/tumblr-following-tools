import pytumblr as py
import pandas as pd
import time
import unicodedata
import httplib
import httplib2
import random
import socket
import sys
from selenium import webdriver
from path import Path as path
from PIL import Image

usual_suspects = (IOError, httplib.HTTPException, httplib2.ServerNotFoundError, socket.error, socket.timeout)

default_timeout = 10;

def randdelay(a,b):
    time.sleep(random.uniform(a,b))

def getClient(credentials):
    df = pd.read_csv(credentials)
    client = py.TumblrRestClient(df['ConsumerKey'][0], df['ConsumerSecret'][0], df['OauthToken'][0], df['OauthSecret'][0])
    return client


def cleanup(myblog, mylist, fdays=50):
    newlist = []
    for i in mylist:
        try:
            tmp = myblog.blog_info(i.rstrip())
            updated = tmp['blog']['updated']
            tmptime = (time.time() - updated )/86400.0
            if tmptime < fdays:
                newlist.append(i)
        except KeyError:
            pass              
    return newlist

def isimage(myfile):
    try:
        Image.open(myfile)
        return True
    except IOError:
        return False
    
def name(myblog,blogNumber=0):
    goahead = False
    while goahead == False:
        try:
            minfo = myblog.info()
            minfo2 = minfo['user']['blogs'][blogNumber]
            targetBlog = u_to_s(minfo2['name'])
            goahead = True
        except usual_suspects:
            goahead = False
    return targetBlog   

def load_tumblr_csv(myfile):
    tmp = pd.read_csv(myfile, header=None).values.tolist()
    tmp2 = []
    for i in range(0,len(tmp)):
        tmp2.append(tmp[i][0])
    return tmp2

def save_tumblr_csv(myfile, mylist):
    tmp = pd.DataFrame(mylist)
    tmp.to_csv(myfile, index=False, header = False)

def bulk_scrape_users(myfile):
    import scrape_users
    browser = webdriver.Firefox()
    tmp = set(load_tumblr_csv(myfile))
    everybody = []
    reblogged = []
    liked = []
    for i in tmp:
        try:
            (a,b,c) = scrape_users.runme(i,browser=browser)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            print i
            browser.close()
            return((list(set(everybody)),list(set(reblogged)),list(set(liked))))
        everybody += a
        reblogged += b
        liked += c
    browser.close()
    return((list(set(everybody)),list(set(reblogged)),list(set(liked))))

def tumblr_follow_html(mylist,outfile="followme.html"):
    n = len(mylist)
    f = open(outfile,'w')
    for i in range(0,n):
        myurl = strip_tumblr(mylist[i])
        mystr = "<p><a href=\"http://www.tumblr.com/follow/{}\" target=\"blank\">{}</a></p>\n".format(myurl,myurl)
        f.write(mystr)
    f.close()

def auto_unfollow(mylist, myclient, verbose=False, timeout = default_timeout):
    n = len(mylist)
    socket.setdefaulttimeout(timeout)
    for i in range(0,n):
        randdelay(1,3)
        if verbose == True:
            print "Trying blog #:{}".format(1+i)
        goahead = False
        while goahead == False:
            try:
                tmp = myclient.unfollow(mylist[i])
                goahead = True
                if verbose == True:
                    print "\n{}\n".format(tmp)
            except usual_suspects:
                goahead = False
    
def strip_tumblr(mystr):
    mystr = mystr.rstrip()
    if len(mystr) < 11:
        return mystr
    elif mystr[len(mystr)-11:] == ".tumblr.com":
        return mystr[0:len(mystr)-11]
    else:
        return mystr

def append_tumblr(mystr):
    mystr = mystr.rstrip()
    if len(mystr) < 11:
        return mystr + ".tumblr.com"
    elif mystr[len(mystr)-11:] == ".tumblr.com":
        return mystr
    else:
        return mystr + ".tumblr.com"

def same_tumblr(a,b):
    a2 = strip_tumblr(a)
    b2 = strip_tumblr(b)
    return (a2 == b2)

def find_tumblr(mykey,mylist):
    n = len(mylist)
    i = 0
    while i < n:
        if same_tumblr(mykey, mylist[i]):
            return True
        i += 1
    return False

def u_to_s(uni):
    return unicodedata.normalize('NFKD',uni).encode('ascii','ignore')

def blogname(myraw,i):
    return u_to_s(myraw[i]['uuid'])

def staleBlogs(myblog = None, myraw = None, days=50, verbose=False):
    if myraw == None:
        myraw = rawF(myblog.following, verbose = verbose)
    fdays = float(days)
    result = []
    for i in range(0,len(myraw)):
        tmptime = (time.time() - myraw[i]['updated'] )/86400.0
        if tmptime > fdays:
            result.append(blogname(myraw,i))
    return result
    

def rawF(myfunction, waittime = 1, autorestart = True, verbose = False, cutoff = None, timeout = default_timeout): #myfunction default: client.following
    socket.setdefaulttimeout(timeout)
    goahead = False
    while goahead == False:
        try:
            n = myfunction()['total_blogs']
            goahead = True
        except usual_suspects:
            goahead = False
    if cutoff != None:
        n = min(n,cutoff)
    m = 20
    rem = n % m
    cycles = n/m
    result = []
    for i in range(0,cycles):
        if verbose == True:
            print "Trying Blogs {} to {}".format(m*i + 1, m*i + m)
        params = {'offset': m*i, 'limit': m}
        goahead = False
        while goahead == False:
            try:
                time.sleep(waittime)
                tmp = myfunction(**params)
                goahead = True
            except usual_suspects:
                goahead = False
        result = result + tmp['blogs']
    params = {'offset': m*cycles, 'limit': rem}
    if verbose == True:
        print "Finishing..."
    if rem != 0:
        goahead = False
        while goahead == False:
            try:
                time.sleep(waittime)
                tmp = myfunction(**params)
                goahead = True
            except usual_suspects:
                goahead = False
        result = result + tmp['blogs']
    return result

def getFollowers(myblog, waittime = 1, autorestart = True, verbose = False, cutoff = None, timeout = default_timeout, targetBlog = None, blogNumber=0):
    socket.setdefaulttimeout(timeout)
    goahead = False
    while goahead == False:
        try:
            minfo = myblog.info()
            minfo2 = minfo['user']['blogs'][blogNumber]
            if targetBlog == None:
                targetBlog = u_to_s(minfo2['name'])
            n = myblog.followers(targetBlog)['total_users']
            goahead = True
        except usual_suspects:
            goahead = False

    if cutoff != None:
        n = min(n,cutoff)
    m = 20
    rem = n % m
    cycles = n/m
    result = []    
    for i in range(0,cycles):
        if verbose == True:
            print "Trying Blogs {} to {}".format(m*i + 1, m*i + m)
        params = {'offset': m*i, 'limit': m}
        goahead = False
        while goahead == False:
            try:
                time.sleep(waittime)
                tmp = myblog.followers(targetBlog,**params)
                goahead = True
            except usual_suspects:
                goahead = False
        result = result + tmp['users']
    params = {'offset': m*cycles, 'limit': rem}
    if verbose == True:
        print "Finishing..."
    if rem != 0:
        goahead = False
        while goahead == False:
            try:
                time.sleep(waittime)
                tmp = myblog.followers(targetBlog,**params)
                goahead = True
            except usual_suspects:
                goahead = False
        result = result + tmp['users']
    return result
    
def getPosts(myblog, waittime = 1, autorestart = True, verbose = False, cutoff = None, timeout = default_timeout, targetBlog = None, blogNumber=0, blogtype=None, blogcutoff = None):
    socket.setdefaulttimeout(timeout)
    goahead = False
    while goahead == False:
        try:
            minfo = myblog.info()
            goahead = True
        except usual_suspects:
            goahead = False
    minfo2 = minfo['user']['blogs'][blogNumber]
    n = minfo2['posts']
    if targetBlog == None:
        targetBlog = u_to_s(minfo2['name'])
    else:
        tmpinfo = myblog.blog_info(targetBlog)
        n = tmpinfo['blog']['posts']
    if cutoff != None:
        n = min(n,cutoff)
    m = 20
    rem = n % m
    cycles = n/m
    result = []
    breakfor = False
    for i in range(0,cycles):
        if verbose == True:
            print "Trying Posts {} to {}".format(m*i + 1, m*i + m)
        params = {'offset': m*i, 'limit': m, 'reblog_info': True}
        if blogtype is not None:
            params['type'] = blogtype
        goahead = False
        while goahead == False:
            try:
                time.sleep(waittime)
                tmp = myblog.posts(targetBlog,**params)
                if blogcutoff is not None:
                    for t in tmp['posts']:
                        if t['id'] == blogcutoff:
                            breakfor = True
                goahead = True
            except usual_suspects:
                goahead = False
        try:
            result = result + tmp['posts']
        except KeyError:
            pass
        if breakfor:
            break
    params = {'offset': m*cycles, 'limit': rem, 'reblog_info': True}
    if blogtype is not None:
        params['type'] = blogtype
    if verbose == True:
        print "Finishing..."
    if rem != 0:
        goahead = False
        while goahead == False:
            try:
                time.sleep(waittime)
                tmp = myblog.posts(targetBlog,**params)
                goahead = True
            except usual_suspects:
                goahead = False
        result = result + tmp['posts']
    return result 

def getImagePosts(myblog, myposts = None, verbose=True, blogNumber=0, targetBlog = None, blogcutoff=None, ignore_reblogs = False):
    if myposts is None:
        myposts = getPosts(myblog, waittime = 1, autorestart = True, verbose = verbose, cutoff = None, timeout = default_timeout, targetBlog = targetBlog, blogNumber=blogNumber, blogtype="photo", blogcutoff = blogcutoff)
    dates = []
    postURLs = []
    imageURLs = []
    notes = []
    reblog = []
    _id = []
    for p in myposts:
        if ((p['trail'] == []) or (ignore_reblogs == False)) & (u_to_s(p['type']) == 'photo'):
            dates.append(u_to_s(p['date']))
            postURLs.append(u_to_s(p['post_url']))
            imageURLs.append(u_to_s(p['photos'][0]['original_size']['url']))
            notes.append(p['note_count'])
            reblog.append(p['reblog_key'])
            _id.append(p['id'])
    results = pd.DataFrame()
    results['Date'] = dates
    results['Post URL'] = postURLs
    results['Image URL'] = imageURLs
    results['Notes'] = notes
    results['reblog_key'] = reblog
    results['id'] = _id
    return results
    
def getPostTitles(posts):
    titles = []
    for p in posts:
        try:
            mytitle = p['title']
            tmptitle = u_to_s(mytitle)
            if len(tmptitle) > 0:
                titles.append(tmptitle.replace("\r","").replace("\n",""))
        except TypeError:
            pass
        except KeyError:
            try:
                mytitle = p['summary']
                tmptitle = u_to_s(mytitle)
                if len(tmptitle) > 0:
                    titles.append(tmptitle.replace("\r","").replace("\n",""))
            except (TypeError, KeyError):
                pass
    return titles
                

def getF(myfunction=None, flist = None, waittime=1, myraw = None, cutoff = None, verbose = False, timeout = 10): #myfunction default: client.following
    if flist == None:
        if myraw == None:
            myraw = rawF(myfunction = myfunction, waittime = waittime,cutoff = cutoff, verbose = verbose, timeout = timeout)
        result = []
        for i in range(0,len(myraw)):
            result.append(blogname(myraw,i))
        return result
    else:
        return load_tumblr_csv(flist) 
#CSV Structure:
#Column 1: blog name
#Column 2: post id
#Column 3: reblog key        
def mass_queue(myblog, myblogname, mycsv):
    myqueue = pd.read_csv(mycsv, header=None)
    for i in xrange(0,len(myqueue)):
        myblog.reblog(myblogname,id=myqueue.loc[i,1],reblog_key=myqueue.loc[i,2],state="queue")
        
def queue_folder(myblog, myblogname, folder, tags=[]):
    myfolder = path(folder)
    for f in myfolder.files():
        if isimage(f) == True:
            myblog.create_photo(myblogname, state="queue", tags=tags, data=str(f))
            
def get_all_files(folder):
    f = path(folder)
    folders = f.dirs()
    files = f.files()
    result = files
    for i in folders:
        result += get_all_files(i)
    return result
    
def get_random_images(folder, num):
    files = get_all_files(folder)
    random.shuffle(files)
    images = []
    i = 0
    while (len(images) < num) & (i < len(files)):
        test = files[i]
        i += 1
        if isimage(test) == True:
            images.append(test)
    return images
    
def copy_random_images(source, destination, num):
    images = get_random_images(source, num)
    for i in images:
        f = path(i)
        f.copy(destination + "/" + f.namebase + str(random.randint(1,1000000000)) + f.ext)      
        
def follow_wizard(target,myfollowing,maxfollow=200):
    targets = 0
    random.shuffle(target)
    n = len(target)
    i = 0
    result = []
    while (targets < maxfollow) & (i < n):
        finder = find_tumblr(target[i],myfollowing)
        if finder == False:
            targets += 1
            result.append(target[i].rstrip())
        i += 1
    return result
            