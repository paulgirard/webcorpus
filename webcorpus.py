# -*- coding: utf-8 -*-

#
# webcorpus library in python
# se navicrawler issuecrawler
#
# repository : http://github.com/paulgirard/webcorpus
# documentation : http://packages.python.org/webcorpus
#
# main developper : Paul Girard, médialab Sciences Po
# licence : GPL v3
#



from lxml import etree
from lxml import objectify
import re,time
from copy import deepcopy
import sys

verbose=False

def _print(arg):
	if verbose :
		print arg

class Link():

	def __init__(self,_from,_to,weight=1):
		self._from=_from
		self._from.hub+=1
		self._to=_to
		self._to.authority+=1
		self.weight=weight
	
	def addParallel(self):
	# should parallel link count into hub and authority calculations ? 
		self.weight+=1
		self._from.hub+=1
		self._to.authority+=1
		
	def __str__(self):
		return str(self._from)+" -> "+str(self._to)+" "+str(self.weight)


class Links(list):

	def __init__(self,_from):
		self._from=_from
		self.tos=dict()
	
	def add(self,_to):
		if _to.id in self.tos.keys():
			self.tos[_to.id].weight+=1
		else :
			self.tos[_to.id]=Link(self._from,_to)
	
	def __iter__(self):
		return self.tos.itervalues()
		
	def __getitem__(self,index) :
		return self.tos[index]
		
	def __str__(self) :
		if len(self.tos)>0 :
			return "\n".join([str(link) for link in self.tos.itervalues()])
		else :
			return str(self._from)+" no links "

# website object
class Website() :
	
	def __init__(self,host,url=""):
		self.id=host
		if url=="" :
			self.url="http://"+("www."+host if len(host.split("."))<3 else host)
		else :
			self.url=url
		self.host=host
		self.links=Links(self)
		self.authority=0
		self.hub=0
		self.pages=dict()
		
	def linkTo(self,website):
		self.links.add(website)
	
	def addPage(self,id,url):
		self.pages[id]=Page(id,url,self)
		return self.pages[id]
		
	def __str__(self):
		return self.host


# page object
class Page():
	website=None
	
	def __init__(self,id,url,website):
		self.id=id
		self.url=url
		self.website=website
		self.authority=0
		self.hub=0
		self.links=Links(self)
		
	def linkTo(self,page):
		# page level link
		self.links.add(page)
		# website level link
		self.website.linkTo(page.website)
		
	def __str__(self):
		return self.url
		
class WebCorpus():

	def __init__(self):
		self.websites=dict()
		self.pages=dict()
		self.date=time.strftime("%a %b %d %Y %H:%M:%S %Z", time.gmtime())
		self.starting_points=[]
	
	def load_from_issuecrawler(self,filename) :		
		# open issuecrawler
		xmlfile=open(filename)

		# objectify
		tree= objectify.parse(xmlfile)
		root=tree.getroot()

		self.date=time.strftime("%a %b %d %Y %H:%M:%S %Z",time.strptime(root.Statistics.CrawlEnd.get('datestamp'),"%Y-%m-%d %H:%M:%S"))


		
		# load starting points
		for startingpoint in root.StartingPoints.StartingPoint :
			host=re.sub("http://","",startingpoint.get("URL")) 
			host=re.sub("www.","",host)
			self.starting_points.append(host)

		#load pages and websites
		for site in root.PageList.Site :
			self.websites[site.get('host')]=Website(site.get('host'),site.get('URL'))
			try : 
				for page in	site.Page :
					self.pages[page.get("ID")]=self.websites[site.get('host')].addPage(page.get("ID"),page.get("URL")) 
			except AttributeError, e:
				pass

		# load external sites
		for es in root.InwardLinks.ExternalSite :
			self.websites[es.get('host')]=Website(es.get('host'))
			
		
		# load links
		def autopagekey(key=0) :
			while True :
				yield "ep_"+str(key)
				key=key+1
		
		for es in root.InwardLinks.ExternalSite :
			website=self.websites[es.get('host')]
			for ep in es.ExternalPage :
				#externalePage doesn't have any id
				pageid=autopagekey()
				self.pages[pageid]=website.addPage(pageid,ep.get("URL"))
				for link in ep.Link :
					self.pages[pageid].linkTo(self.pages[link.get('TargetPageID')])
			
	def __str__(self) :
		#return "\n".join([str(link) for link in [links for links in 
		return "\n".join([str(website.links) for website in self.websites.itervalues()])

	def export_to_navicrawler(self,output_filename,libelles_filename=None) :
		
		# libelles
		classements=etree.Element("classements")
		if libelles_filename :
			libelles_file=open(libelles_filename)
			l_tree=objectify.parse(libelles_file)
			libelles_root=l_tree.getroot()
			
			# check if groupe Independant is there
			index_independant=[groupe.get("nom") for groupe in libelles_root.groupeslibelles.groupelibelle].index("Independant")
				
			# add starting point libelle 
			starting_point_xml=etree.SubElement(libelles_root.libelles,"libelle")
			starting_point_xml.set("nom","starting point")
			starting_point_xml.set("groupe",str(index_independant))
			
			
			#prepare classements element to be included
			
			for libelle in libelles_root.libelles.libelle :
				classement= etree.SubElement(classements,"classement")
				_print(libelle.get('nom'))
				classement.set("libelle",libelle.get('nom'))
				classement.set("etat","non-classe")

		else :
			libelles_root=etree.Element("libelles")
		
		_print(etree.tostring(classements))
		
		wxsf=etree.Element("WebatlasXmlSessionFile")
		session=etree.SubElement(wxsf,"session")
		etree.SubElement(session,"origine").text="webcorpus"
		etree.SubElement(session,"date").text=self.date
		session.append(libelles_root.groupeslibelles)
		session.append(libelles_root.libelles)
		
		
		
		sites = etree.SubElement(session,"sites")
		connexions=etree.SubElement(session,"connexions")
		
		for website in self.websites.itervalues() :
			site=etree.SubElement(sites,"site")
					
			site.set("url",website.url)
			site.set("etat","voisin" if len(website.pages)==0 else "visite")
			# classement : add the starting point flag
			site_classements=deepcopy(classements)
			classement= site_classements[[_c.get("libelle") for _c in site_classements].index("starting point")]
			if website.host in self.starting_points :
				classement.set("etat","oui")
			else :
				classement.set("etat","non")	
			site.append(site_classements)
			pages=etree.SubElement(site,"pages")
			for page in website.pages.itervalues() : 
				pagexml=etree.SubElement(pages,"page")
				pagexml.set("url",page.url)
				pagexml.set("prof","0")
				pagexml.set("marque","non")
			etree.SubElement(site,"description_heuristique")
			
			# links
			for link in website.links :
				lien=etree.SubElement(connexions,"lien")
				lien.set("de",link._from.url)
				lien.set("a",link._to.url)		
		
		file=open(output_filename,"w")
		file.write(etree.tostring(wxsf,pretty_print=True,encoding='utf-8'))
		#print etree.tostring(wxsf,pretty_print=True,encoding='utf-8')
		
		
		
	def export_to_gephi() :
		pass

#############
#   MAIN    #
#############

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

