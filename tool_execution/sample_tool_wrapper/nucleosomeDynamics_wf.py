#!/usr/bin/python2.7

import os
import sys
import argparse
import json
import time
import socket # print localhost
import logging
import re
from pprint import pprint
import multiprocessing
#import psutil  # available memory
import subprocess
import shutil
import glob
import tarfile

out_dir=""

class Mugparams(object):
	@staticmethod
	def check_json(json_file):
		logger = logging.getLogger("lg")
		if not os.path.exists(json_file):
			raise argparse.ArgumentTypeError("%s does not exist" % json_file)

		with open(json_file,'r') as file_data:    
			try:
				data = json.load(file_data)
			except  ValueError, e:
				#raise argparse.ArgumentTypeError("%s in not a valid json file. %s" % (json_file,e))
				logger.exception("%s in not a valid json file." % json_file)
			
		return data

	@staticmethod
	def readable_dir(d):
		if not os.path.isdir(d):
			raise Exception("readable_dir:{0} is not a directory path or is not accessible".format(d))
		if os.access(d, os.R_OK):
			return d
		else:
			raise Exception("readable_dir:{0} is not a readable dir".format(d))


	@staticmethod
	def writeable_file(f):
		if not os.path.isfile(f):
			d =  os.path.dirname(f)
			# TODO Fails if relative path given
			if not os.path.isdir(d):
				raise Exception("writeable_file:{0} not in a existing directory path, or not accessible".format(d))
			else:
				if os.access(d, os.W_OK):
					return f
				else:
					raise Exception("writeable_file:{0} is not a writeable dir".format(d))
		else:
			return f

	@staticmethod
	def process_arguments(args):
		global out_dir
		logger = logging.getLogger("lg")

		# Setting working directory (project)
		proj_idx = next(idx for (idx, d) in enumerate(args.config["arguments"]) if d["name"] == "project")
		out_dir = args.root_dir+"/"+args.config["arguments"][proj_idx]["value"]

		logger.info("Output file directory set to %s" % out_dir)
		
		# Indexing config arguments by name
    		arguments_by_name = dict((d["name"], dict(d, index=index)) for (index, d) in enumerate(args.config["arguments"]))
		logger.debug("Configuration file arguments are %s " % arguments_by_name)
	
		return 1




# TODO 
# Mock: copying the results from a real execution

def run_pipeline(args, num_cores):
	results = {}
	logger  = logging.getLogger("lg")

	print "#### CONFIG FILE CONTAINS";	
	for input in args.config["input_files"]:
		print "\tID=%s\t\tID=%s" % (input["name"], input["value"])
	for input in args.config["arguments"]:
		print "\tID=%s\t\tID=%s" % (input["name"], input["value"])

	source_dir = "/orozco/services/Rdata/Web/USERS/ND57d01d39a0810/sample/"
	extensions = ("*.gff","*.RData","*.bw","*csv","*.png")
	files= []
	for extension in extensions:
	    files.extend(glob.glob(source_dir+"/"+extension))
	    files.extend(glob.glob(source_dir+"/."+extension))

	source_dir = "/orozco/services/Rdata/Web/USERS/ND57d01d39a0810/uploads/"
	extensions = ("*RData","*.cov")

	for extension in extensions:
	    files.extend(glob.glob(source_dir+"/"+extension))


	for file in files:
	    if os.path.isfile(file):
		#time.sleep(2)
		shutil.copy2(file, os.getcwd())
		logger.info("Created  %s" % file)

	return 1

#
# Prepare metadata for the output files 

def prepare_results(args):
	
	global out_dir
	logger  = logging.getLogger("lg")

	#print "META IS "
	#print(args.metadata)			
  	#return 0

	if (args.out_metadata):

		# Create out_metadata JSON 
		json_data  = {}
		json_data['output_files']= []

		# Gather output files (here *GFFs and *BWs)
		files      = []
		extensions = ("*.gff", "*bw")
		
		for extension in extensions:
			files.extend(glob.glob(out_dir+"/"+extension))
	
		# Set metadata required for each output file
		for fil in files:
			result = {}

			# Set name. Should coincide with tool.json. Here, if file="NR_blabla.gff", name= "ND_gff"
			p = re.compile('\/([^_\/]*)_[^\/]+\.(.*)$')
			t = p.findall(fil)
			s = p.search(fil)
			prefix = s.group(1)
			ext    = s.group(2)
			out_name = s.group(1) + "_" + s.group(2)
			result["name"]      = out_name

			# Set file_path. Absolute path. Should be better relative to root_dir?
			result["file_path"] = fil

			# Set source_id. Array. Provenance of file, fileIds of the inputs_files which this file derives from. Here, the corresponding MNAse file_id
			result["source_id"] = ["TODO"]
			result["taxon_id"]  = 0
			result["meta_data"] ={}
			result["meta_data"]['assembly']= "R64-1-1"
			
			json_data['output_files'].append(result)
			

		# Prepare last output file: TAR of *CSVs and *PNGs
		files      = []
		extensions = (".*.csv", ".*.png")
		out_tar    =  os.getcwd() + "/results.tar.gz" 

		tar = tarfile.open(out_tar, "w:gz")
		for extension in extensions:
			files.extend(glob.glob(out_dir+"/"+extension))
		for fil in files:
			logger.info ("Packing %s into statistics TAR" % os.path.basename(fil)) 
 			#tar.add(fil)
			#tar.addfile(tarfile.TarInfo("myfilename.txt"), file("/path/to/filename.txt"))
			#tar.addfile(tarfile.TarInfo(os.path.basename(fil)), file(fil))
			tar.add(fil, arcname=os.path.basename(fil))
		tar.close()

		# Set metadata required for TAR output file
		result = {}
		result["name"]      = "statistics"
		result["file_path"] = out_tar
		result["source_id"] = ["TODO"]
		json_data['output_files'].append(result)


		# Write down output file metadata
		J = open(args.out_metadata, 'wb')
		J.write(json.dumps(json_data,indent=4, separators=(',', ': ')))
		J.close
		logger.info("Output files annotated into %s" % args.out_metadata)


def main():

	# Start logging

	logger = logging.getLogger("lg")
	logger.setLevel(logging.INFO)
	formatter = logging.Formatter(fmt='%(asctime)s - %(module)s - %(levelname)s - %(message)s')

	handler = logging.FileHandler('%s.log' %  os.path.splitext(os.path.basename(__file__))[0])
	handler.setLevel(logging.INFO)
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	streamhandler = logging.StreamHandler()
	streamhandler.setLevel(logging.INFO)
	streamhandler.setFormatter(formatter)
	logger.addHandler(streamhandler)

	logger.info('Starting %s' % __file__)

	# Parse CMD

	parser = argparse.ArgumentParser(prog="nucleosomeDynamics_wf",  description="Nucleoseom Dynamics workflow")
		
	parser.add_argument("--config",  required=True,  type=Mugparams.check_json, metavar="CONFIG_JSON",
				help="JSON file containing workflow parameters")
	parser.add_argument("--root_dir",  required=True,  type=Mugparams.readable_dir, metavar="ABS_PATH",
				help="Absolute path of the user data directory.")
	parser.add_argument("--metadata",  required=True,  type=Mugparams.check_json, metavar="METADATA_JSON",
				help="JSON file containing MuG metadata files")
	parser.add_argument("--out_metadata",  required=True,  type=Mugparams.writeable_file, metavar="RESULTS_JSON",
				help="JSON file containing results metadata")
	parser.add_argument("-v", "--verbose", required=False, action="store_true", 
				help="increase output verbosity")
	parser.add_argument('--version', action='version', version='%(prog)s 0.1')

	args = parser.parse_args()

	if args.verbose:
		logger.setLevel(logging.DEBUG)
		handler.setLevel(logging.DEBUG)
		handler.setLevel(logging.DEBUG)
		logger.addHandler(handler)
		streamhandler.setLevel(logging.DEBUG)
		logger.addHandler(streamhandler)
		logger.debug("Verbose mode on")

	# Parse config
	Mugparams.process_arguments(args)


	# Print host info
	
	num_cores = multiprocessing.cpu_count()
	host      = socket.gethostname()
	#mem      = psutil.virtual_memory()
	logger.debug('HOST=%s CPUs=%s MEM=x' %(host,num_cores)) 


	# Run pipeline

	outfiles = run_pipeline(args, num_cores)

	# Results 

	prepare_results(args)

if __name__ == '__main__':
	main()
