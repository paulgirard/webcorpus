from issue2navicrawler import WebCorpus,_print
import sys

if len(sys.argv) < 7 :
	print "usage : python webcorpus.py --from_issuecrawler issuecrawler_filename.xml --to_navicrawler output_filename.wxsf --use_tags tags_file.xml"
	print " add -v for verbose mode"
	exit()

input_filename=sys.argv[sys.argv.index("--from_issuecrawler")+1]
output_filename=sys.argv[sys.argv.index("--to_navicrawler")+1]
tags_filename=sys.argv[sys.argv.index("--use_tags")+1]

if "-v" in sys.argv :
	verbose=True

if "--from_issuecrawler" in sys.argv :
	webcorpus=WebCorpus()
	webcorpus.load_from_issuecrawler(input_filename)
	_print(webcorpus)
	webcorpus.export_to_navicrawler(output_filename,tags_filename)
	print "file "+input_filename+" exported to "+output_filename+" successfully"
