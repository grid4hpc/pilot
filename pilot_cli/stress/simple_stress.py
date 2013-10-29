#!/usr/bin/env python

from multiprocessing import Pool, TimeoutError
from subprocess import Popen, PIPE
from time import time, sleep
import random, sys
from optparse import OptionParser

def test_url(url):
    start = time()
    Popen(['pilot-uri-helper', url], stdout=PIPE, stderr=PIPE).communicate()
    return time() - start

def main():
    parser = OptionParser()
    parser.add_option("-p", "--processes", help="Number of parallel processes (default: %default)", type="int", default=5, metavar="N", dest="processes")
    parser.add_option("-c", "--count", help="Total count of requests to run (default: %default)", type="int", default=1, metavar="N", dest="count")
    opts, _ = parser.parse_args()

    urls = Popen('pilot-query-jobs', stdout=PIPE, stderr=PIPE).communicate()[0].split("\n")
    while(len(urls) < opts.count):
        urls.extend(urls)
    urls = urls[:opts.count]

    random.shuffle(urls)

    pool = Pool(opts.processes)
    print "Running %d queries using %d processes." % (opts.count, opts.processes)
    results_map = pool.map_async(test_url, urls)
    while True:
        try:
            results_map = results_map.get(1)
            print
            break
        except TimeoutError:
            sys.stdout.write(".")
            sys.stdout.flush()

    print "Average: %f, min: %f, max: %f" % (
        sum(results_map)/float(len(results_map)),
        min(results_map), max(results_map))
    
if __name__ == '__main__':
    main()
