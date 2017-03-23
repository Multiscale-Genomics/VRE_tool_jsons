#!/usr/bin/python2.7

import os
import sys
import argparse
import json
import time
import socket # print localhost
import logging
import re
import pprint
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
    		arguments_by_name = dict((d["name"], d["value"]) for (index, d) in enumerate(args.config["arguments"]))
		args.config["arguments"] = arguments_by_name

		# Indexing config input_files by name (name could not be unique - because of allow_multiple)
    		inputs_by_name = {}
		for index,d in enumerate(args.config["input_files"]):
			name = args.config["input_files"][index]["name"]
			if name in inputs_by_name:
				pprint.pprint(inputs_by_name[name])
				if type(inputs_by_name[name] is str):
					prev = inputs_by_name[name]
					inputs_by_name[name]= list()
					inputs_by_name[name].append(prev)
				inputs_by_name[name].append(d["value"])
			else:
				inputs_by_name[name]=d["value"]
		args.config["input_files"] = inputs_by_name
		logger.debug("Configuration file arguments and input_files are:\n %s " % pprint.pformat(args.config))
		return 1

	@staticmethod
	def process_metadata(args):
		global out_dir
		logger = logging.getLogger("lg")

		# Indexing metadata files by file_id ([_id])
    		metadata_by_id = dict((d["_id"], dict(d)) for (index, d) in enumerate(args.metadata))
		args.metadata = metadata_by_id
		logger.debug("VRE metadata for input_files is:\n %s " % pprint.pformat(args.metadata))
	
		return 1





# TODO 
# Mock: copying the results from a real execution

def run_pipeline(args, num_cores):
	results = {}
	logger  = logging.getLogger("lg")

	print "#### CONFIG FILE CONTAINS";	
	for in_name in args.config["input_files"]:
		print "\tID=%s\t\tVALUE=%s" % (in_name, args.config["input_files"][in_name])
	for arg_name in args.config["arguments"]:
		print "\tID=%s\t\tVALUE=%s" % (arg_name, args.config["arguments"][arg_name])

	mock_files = ["NR_sample_cellcycle_G1.gff"]

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
	
		# Set metadata required for each GFF and BW output file
		for fil in files:
			result = {}

			# Set name
			# Should coincide with tool.json. In nucldyn, if fil="NR_blabla.gff", output_files.name="NR_gff"
			p = re.compile('\/([^_\/]*)_([^\/]+)\.(.*)$')
			t = p.findall(fil)
			s = p.search(fil)
			prefix    = s.group(1)
			rootname  = s.group(2)
			extension = s.group(3)

			out_name = prefix + "_" + extension
			result["name"]      = out_name

			# Set file_path
			# Absolute path. Should be better relative to root_dir?
			result["file_path"] = fil

			# Set source_id & taxon_id
			# source_id is the list of inputs_files (file_ids) that this file derives from. In nucldyn, file="NR_blabla.gff" derives from "blabla.bam" (except 'ND_gff')
			result["source_id"] = []
			if out_name == "ND_gff":
				for input_id,file_id in args.config['input_files'].iteritems():
					if (input_id == "condition1" or input_id == "condition2"):
						result["source_id"].append(file_id);
			else:
				for file_id,file_meta in args.metadata.iteritems():
					input_file_path = file_meta['file_path']
					input_basename  = os.path.basename(input_file_path)
					input_rootname  = os.path.splitext(input_basename)[0]
					
					if rootname == input_rootname:
						result["source_id"].append(file_id)

			# Set taxon_id
			# taxon_id is inherited from the input file (i.e the source_id)
			result["taxon_id"]  = 0
			if result["source_id"]:
				for file_id in result["source_id"]:
					if args.metadata[file_id]["taxon_id"]:
						result["taxon_id"] = args.metadata[file_id]["taxon_id"]
						break
					
			# Set meta_data->assembly
			# taxon_id is inherited from the input file (i.e the source_id)
			result["meta_data"] ={}
			result["meta_data"]['assembly']= ""
			if result["source_id"]:
				for file_id in result["source_id"]:
					if args.metadata[file_id]["meta_data"]["assembly"]:
						result["meta_data"]['assembly']= args.metadata[file_id]["meta_data"]["assembly"]
			
			# Append output_file metadata into JSON data
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
	parser.add_argument("--public_dir",  required=False,  type=Mugparams.readable_dir, metavar="PUBLIC_PATH",
				help="Absolute path of the MuG public directory (with reference genome data, etc).")
	parser.add_argument("--metadata",  required=True,  type=Mugparams.check_json, metavar="METADATA_JSON",
				help="JSON file containing MuG metadata files")
	parser.add_argument("--out_metadata",  required=False,  type=Mugparams.writeable_file, metavar="RESULTS_JSON",
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
	Mugparams.process_metadata(args)


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
