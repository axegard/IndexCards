#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, redirect, g, url_for, send_from_directory
import datetime
import sqlite3
import os
from werkzeug.utils import secure_filename

import db_handler

app = Flask(__name__)
#from bson.objectid import ObjectId

#### Config SQLite ####
DATABASE = '../db/letters.db'


#!/usr/bin/env python
# -*- coding: utf-8 -*-

def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DATABASE)
	return db

def query_db(query, args=(), one=False):
	if "SELECT" in query:
		cur = get_db().execute(query, args)
		rv = cur.fetchall()
		cur.close()
	elif "INSERT" in query:
		cur = get_db().execute(query, args)
		rv = get_db().commit()
		cur.close()
	return (rv[0] if rv else None) if one else rv


#### Configure iamge upload
UPLOAD_FOLDER = '../images/'
STATIC_FOLDER = '../static'
ALLOWED_EXTENSIONS = set(['png','jpg','jpeg','gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def front():
	return render_template('main.html')

@app.route('/search/')
#@app.route('/search/<sender>')

def return_search():
	GET_keywords = request.args.get('keywords')
	GET_sender = request.args.get('correspondent_1')
	GET_correspondent_2 = request.args.get('correspondent_2')
	GET_sender_ID = request.args.get('sender_id')
	GET_year = request.args.get('year')
	GET_month = request.args.get('month')
	GET_day = request.args.get('day')
	GET_view = request.args.get('view')
# Prepare GET-variables
	# GET_sender
	if GET_sender is None:
		GET_sender = ""
	else:
		GET_sender = GET_sender.encode('utf8')

	if GET_correspondent_2 is None:
		GET_correspondent_2 = ""
	else:
		GET_correspondent_2 = GET_correspondent_2.encode('utf8')
	# GET_year
	if isinstance(GET_sender, str):
		# Find a name  LIKE % ' + GET_sender + '% OR has GET_sender_ID
		if GET_sender_ID is not None:
			author = query_db("SELECT pk_PersonID,Title,Forenames,Surname,BirthDate,DeathDate FROM tblPerson WHERE pk_PersonID = ?",[GET_sender_ID])
		else:
			author = query_db("SELECT pk_PersonID,Title,Forenames,Surname,BirthDate,DeathDate FROM tblPerson WHERE FullNameTemp LIKE '%" + GET_sender + "%'")

		correspondent_2 = query_db("SELECT pk_PersonID,Title,Forenames,Surname,BirthDate,DeathDate FROM tblPerson WHERE FullNameTemp LIKE '%" + GET_correspondent_2 + "%'")
		if len(author) == 1 and len(GET_correspondent_2) == 0:
		# Print all correspondence of author!
		# We got a single match!
			# Far icke att fungera :/ 
				# author = query_db("SELECT pk_PersonID,Title,Forenames,Surname FROM tblPerson WHERE FullNameTemp LIKE '%?' or Forenames LIKE '%?'", (GET_sender, GET_sender))


			author_ID = author[0][0] #Author_ID is list of tuples. Tuple av int.
			author_name = str(author[0][1]) + " " + str(author[0][2]) + " " + str(author[0][3]) # Title + Forenames + Surname

			# Gets all articles associated with fk_PersonID_author
			response_SELECT_tblMaster =  query_db("SELECT pk_WCP_Number,Year,Month,Day,fk_PersonID_Addressee,fk_PersonID_Author FROM tblMaster WHERE fk_PersonID_Author = ?", [str(author_ID)])
			# SQL-lite: parametrized

			addressee_dict = {}
			for row in response_SELECT_tblMaster:
				if row[4] in ['Null','',0,None]: # dvs om Person är unknown
					fk_PersonID_Addressee = 0
				else:
					fk_PersonID_Addressee = row[4]
				Person_Name = query_db("SELECT Title,Forenames,Surname,FullNameTemp FROM tblPerson WHERE pk_PersonID = ?", [str(fk_PersonID_Addressee)])
				if fk_PersonID_Addressee == 0:
					addressee_name = Person_Name[0][2]
				# SQL_lite: parametrized
				else: #dvs för att utom PersonID = 0, dvs unknown
					addressee_name = Person_Name[0][0] + " " + Person_Name[0][1] + " " + Person_Name[0][2]
#				# Todo: FullNameTemp (ie Person_Name[0][3] is not consistently used.. Remove?
				addressee_dict[fk_PersonID_Addressee] = addressee_name

#			author = len(author)
			return render_template('results.html', author_ID = author_ID, author_name = author_name, GET_year = GET_year, response_SELECT_tblMaster=response_SELECT_tblMaster, addressee_dict=addressee_dict, author=author)
		elif len(author) == 1 and len(correspondent_2) == 1:
			print "Hi"
			# Print all correspondence between author and correspondent_2
		elif len(author) > 1 or len(correspondent_2) > 1:
			# We got multiple hits for both author and correspondent_2
			# Sker om query matchar fler än en 'author', d.v.s. flera matchningar i DB => användar får välja villken träff som gäller
			author_ID = ''
			author_name = ''
			GET_year = GET_year
			response_SELECT_tblMaster = ''
			addressee_dict = {}
			return render_template('results.html', author_ID = author_ID, author_name = author_name, GET_year = GET_year, GET_sender = GET_sender, response_SELECT_tblMaster=response_SELECT_tblMaster, addressee_dict=addressee_dict, author=author)
		elif len(author) > 1 and len(correspondent_2) == 1:
			# We got multiple hits for author, but a single match for correspondent_2
			sys.exit()
		elif len(author) == 1 and len(correspondent_2) > 1:
			# We got a single match for author, but multiple hits for correspondent_2
			sys.exit()
		else:
			# No hits for either correspondent in DB
			addressee_dict = {}
			author_ID = ''
			GET_sender = request.args.get('sender')
			author_name = GET_sender
			GET_year = GET_year
			response_SELECT_tblMaster = []
			return render_template('results.html', author_ID = author_ID, author_name = author_name, GET_year = GET_year, response_SELECT_tblMaster = response_SELECT_tblMaster,addressee_dict=addressee_dict, author=author)

#todo                   ***********************************
#todo				************ Letter ****************
#todo				   ***********************************

@app.route('/letter/')
def return_letter():
# Kan man inte typ bara korta ned denna .. och direkt använda URL-id:t???

	if None in [request.args.get('id')]:
		return redirect('/')
	GET_id = request.args.get('id').encode('utf8')
	GET_id = filter(lambda x: x.isdigit(), GET_id)		#only allows int (SQL-filter)


	if request.args.get('p') in [None,'']:
		page_GET = None
	else:
		page_GET = request.args.get('p').encode('utf8')
#		page_GET = page_GET.replace('.jpg','')
		page_GET = int(page_GET)
#		page_GET = filter(lambda x: x.isdigit(), page_GET)  # only allows int (SQL-filter)

# Get contents of master table
	db_tblMaster_columns = ["pk_WCP_Number","TempNumber","ParentRecordType","fk_PersonID_Author","AuthorInferred","AuthorUncertain",
							"fk_AddressID_Author","AuthorsAddressInferred","AuthorsAddressUncertain","fk_PersonID_Addressee","AddresseeInferred",
							"AddresseeUncertain","fk_AddressID_Addressee","AddresseesAddressInferred","AddresseesAddressUncertain","Day","DayInferred",
							"DayUncertain","Month","MonthInferred","MonthUncertain","Year","YearInferred","YearUncertain","NotesLetterDate","Summary",
							"ScrutinySumm","fk_EditorID_RecordCreator","RecordDate","HideRecord"]
	response_SELECT_tblMaster = query_db("SELECT * from tblMaster WHERE pk_WCP_Number = ?", [GET_id])

	# Dictionary type of data from tblMaster
	item_tblMaster_dict = {}
	for column_name in db_tblMaster_columns:
		item_tblMaster_dict[column_name] = response_SELECT_tblMaster[0][db_tblMaster_columns.index(column_name)]

	item_tblMaster_dict['AddresseeUncertain'] = 'a'

# Columns and comments of item_tblMaster_dict
	#pk_WCP_Number					# used
	#TempNumber					# N/A
	#ParentRecordType				# N/A, for now only letters
	#fk_PersonID_Author				# used/implemented
	#AuthorInferred					# todo how? N/A?
	#AuthorUncertain				# todo how? N/A?
	#fk_AddressID_Author				# todo
	#AuthorsAddressInferred				# todo how? N/A?
	#AuthorsAddressUncertain			# todo how? N/A?
	#fk_PersonID_Addressee				# in use/implemented.
	#AddresseeInferred				# todo how? N/A?
	#AddresseeUncertain				# todo how? N/A?
	#fk_AddressID_Addressee				# todo
	#AddresseesAddressInferred			# todo how? N/A?
	#AddresseesAddressUncertain			# todo how? N/A?
	#Day						# in use/implemented. Used to display date
	#DayInferred					# todo how? N/A?
	#DayUncertain					# todo how? N/A?
	#Month						# in use/implemented. Used to display date
	#MonthInferred					# todo how? N/A?
	#MonthUncertain					# todo how? N/A?
	#Year						# in use/implemented. Used to display date
	#YearInferred					# todo how? N/A?
	#YearUncertain					# todo how? N/A?
	#NotesLetterDate				# in use/implemented
	#Summary					# in use/implemented. Used to display summary
	#ScrutinySumm					# todo
	#fk_EditorID_RecordCreator			# in use/implemented.
	#RecordDate					# in use/implemented.
	#HideRecord					# todo

	author_ID = item_tblMaster_dict['fk_PersonID_Author']
	author_Name = query_db("SELECT Title,Forenames,Surname FROM tblPerson WHERE pk_PersonID = ?", [str(author_ID)])
	if len(author_Name) == 0:
		author_FullName = ''
	else:
		author_Name = author_Name[0] #Remove SQL-formating
		author_FullName = author_Name[0] + " " + author_Name[1] + " " + author_Name[2]
	# Reuse item_tblMaster_dict to include author name. item_tblMaster_dict used in HTML template.
	item_tblMaster_dict['sender_name'] = author_FullName


	addressee_ID = item_tblMaster_dict['fk_PersonID_Addressee']
	addressee_Name = query_db("SELECT Title,Forenames,Surname FROM tblPerson WHERE pk_PersonID = ?", [str(addressee_ID)])
	if len(addressee_Name) == 0:
		addressee_FullName = ''
	else:
		addressee_Name = addressee_Name[0] # Remove 'SQL-formating'
		addressee_FullName = addressee_Name[0] + " " + addressee_Name[1] + " " + addressee_Name[2]
	# Reuse item_tblMaster_dict to include addressee name. item_tblMaster_dict used in HTML template.
	item_tblMaster_dict['addressee_name'] = addressee_FullName
	#debug = ["author_ID", author_ID, "addressee_ID", addressee_ID]

# Get contents of items associated with pk_WCP_Number
	db_tblItem_columns = ["pk_ItemID","fk_WCP_Number","fk_ItemTypeID","fk_ProvenanceID","FindingNo","ItemDescription",
			"ItemNotes","fk_ReferenceID","PagePublished","PubNotes","TotalPages","TextPages",
			"fk_LetterTypeID","fk_TextTypeID","fk_InHandOfID","fk_SignedByID","fk_CopyTypeID","fk_TextConditionID",
			"Language","PhysDescInfo","fk_PersonID_Copyright","fk_CopyrightID","fk_ProvenanceID_CopyrightHolder",
			"HideImages","TranscriptFileName","fk_EditorID_Transcriber","TranscriptionDate","ScrutinyTrans",
			"fk_EditorID_SignedOff","DateSignedOff","HideTranscript","ScrutinyRecord","fk_EditorID_RecordCreator","RecordDate"]
	# Fetch letter information
	pk_ItemID = item_tblMaster_dict['pk_WCP_Number']


	response_SELECT_tblItem = query_db("SELECT * from tblItem WHERE pk_ItemID = ?", [pk_ItemID])


	item_tblItem_dict = {}
	for column_name in db_tblItem_columns:
		item_tblItem_dict[column_name] = response_SELECT_tblItem[0][db_tblItem_columns.index(column_name)]

#		item_tblItem_dict['fk_InHandOfID']
# Columns and comments of item_tblItem_dict
	pk_ItemID = item_tblItem_dict['pk_ItemID']							#todo: behövs vid redigering!
	#fk_WCP_Number
	#fk_ItemTypeID						# Default to 1, for now. Atm only letters and not any other types of media
	#fk_ProvenanceID					# Unclear provenance (harr harr)
	#FindingNo							# todo: local item ID of holder?
	#ItemDescription					# todo
	#ItemNotes							# todo
	#fk_ReferenceID						# in use/implemented.  Used to SELECT * from tblReference
	#PagePublished						# N/A?
	#PubNotes							# N/A?
	#TotalPages							# todo?
	#TextPages							# N/A?
	#fk_LetterTypeID					# N/A
	#fk_TextTypeID						# N/A
	#fk_InHandOfID						# in use/implemented. Used to SELECT * from tblInHandOf
	#fk_SignedByID						# N/A, superfluos
	#fk_CopyTypeID						# N/A
	#fk_TextConditionID					# N/A for now
	#Language							# in use/implemented. Prints language if Language|length > 0
	#PhysDescInfo						# N/A for now
	#fk_PersonID_Copyright				# todo
	#fk_CopyrightID						# todo
	#fk_ProvenanceID_CopyrightHolder	# N/A?
	#HideImages							# todo: HideImages = 1, hides images. Implement!
	#TranscriptFileName					# in use/implemented. Used for transcript text
	#fk_EditorID_Transcriber			# todo
	#TranscriptionDate					# in use/implemented
	#ScrutinyTrans						# todo
	#fk_EditorID_SignedOff				# todo
	#DateSignedOff						# todo
	#HideTranscript						# HideTranscript = 1 hides transcript
	#ScrutinyRecord						# todo
	#fk_EditorID_RecordCreator			# todo
	#RecordDate							# todo/done?


	# items_table/item_head/items fanns här (i render_template) innan. Togs bort ty odef. Oklart fkn.
	# Todo: döp om item_head_dict -> item_tblMaster_dict i template när putsa
	link = str(request.url_root) + "letter/" + "?id=" + str(GET_id)

# Get contents of Edition table (tblReference)
	db_tblReference_columns = ["pk_ReferenceID", "Authors", "YearPrinted", "YearPublished", "Title", "Website",
							   "WebsiteURL", "DateAccessed", "Publication", "Series", "Volume", "Part", "PageRange",
							   "InAuthor", "BookTitle", "Publisher", "BookPages", "NotesRef", "TempPageCited"]

	response_SELECT_tblReference = query_db("SELECT * from tblReference WHERE pk_ReferenceID = ?", [item_tblItem_dict['fk_ReferenceID']])

	item_tblReference_dict = {}
	for column_name in db_tblReference_columns:
		if len(response_SELECT_tblReference) > 1:
			item_tblReference_dict[column_name] = response_SELECT_tblReference[0][db_tblReference_columns.index(column_name)]
		else: # len() = 0 if no edition (reference) available.
			item_tblReference_dict[column_name] = ''

# Todo: implement handling of multiple editions...
# item_tblReference_dict['YearPublished'],item_tblReference_dict['Title']
# Columns and comments of tblReference
	#pk_ReferenceID						# in use/implemented
	#Authors							# todo
	#YearPrinted						# todo
	#YearPublished						# in use/implemented
	#Title								# in use/implemented
	#Website							# todo
	#WebsiteURL							# todo
	#DateAccessed						# todo
	#Publication						# todo
	#Series								# todo
	#Volume								# todo
	#Part								# todo
	#PageRange							# todo
	#InAuthor							# todo
	#BookTitle							# todo
	#Publisher							# todo
	#BookPages							# todo
	#NotesRef							# todo
	#TempPageCited						# todo

	# Get contents of tblInHandOf
	db_tblInHandOf_columns = ["pk_InHandOfID","InHandOf","collection","InHandOfDocumentID"]
	response_SELECT_tblInHandOf = query_db("SELECT * FROM tblInHandOf tblInHandOf WHERE pk_InHandOfID = ?",[item_tblItem_dict['fk_InHandOfID']])

	item_tblInHandOf_dict = {}
	for column_name in db_tblInHandOf_columns:
		if len(response_SELECT_tblInHandOf) > 1:
			item_tblInHandOf_dict[column_name] = response_SELECT_tblInHandOf[0][db_tblInHandOf_columns.index(column_name)]
		else:
			item_tblInHandOf_dict[column_name] = ''

		########################
#Columns and comments of tblImage    ##########
		########################
	# pk_ImageID						 
	# fk_ItemID						 
	# ImageFileName						 
	# SortNo				 
	# PageNo

	# Get contents of tblImage
	db_tblImage_columns = ["pk_ImageID","fk_ItemID","ImageFileName","SortNo","PageNo"]
	response_SELECT_tblImage = query_db("SELECT ImageFileName,PageNo from tblImage WHERE fk_ItemID = ?", [pk_ItemID])

	# Dictionary type of data from tblImage
	# Todo: standardize db_response -> dict conversion!
	item_tblImage_dict = []
	for row in response_SELECT_tblImage:
		ImageFileName = row[0]
		PageNo = row[1]
		item_tblImage_dict.append([ImageFileName,PageNo])
#		item_tblMaster_dict[column_name] = response_SELECT_tblImage[0][db_tblMaster_columns.index(column_name)]


	# Get contents of tblTranscript
	db_tblTranscript_columns = ["pk_TranscriptID","fk_TranscriptID","TranscriptFileName","PageNo"]
	response_SELECT_tblTranscript = query_db("SELECT TranscriptFileName,PageNo from tblTranscript WHERE fk_TranscriptID = ?", [pk_ItemID])

	# Dictionary type of data from tblTranscript
	item_tblTranscript_dict = []
	for row in response_SELECT_tblTranscript:
		TranscriptFileName = row[0]
		TranscriptPageNo = row[1]
		item_tblTranscript_dict.append([TranscriptFileName,TranscriptPageNo])


	#Temp vars for testing
	item_tblMaster_dict['Summary'] = ''
	#item_tblMaster_dict['NotesLetterDate'] = ''
	if item_tblMaster_dict['NotesLetterDate'] is None:
		item_tblMaster_dict['NotesLetterDate'] = ''
	item_tblItem_dict['TranscriptionDate'] = ''
	item_tblItem_dict['HideTranscript'] = ''

	debug = ''
#	for image_name,PageNo in item_tblImage_dict:
#		print(image_name)
#		print(PageNo)

	# om ?p=X är None, men det finns sidor.
	if page_GET is None and len(item_tblImage_dict) > 0:
		return redirect("/letter?id=" + GET_id + "&p=1")
	# om ?p=X är ett heltal, men det inte finns några sidor
	if page_GET is not None and len(item_tblImage_dict) == 0:
		return redirect("letter?id=" + GET_id)
		item_tblImage_dict = []
		item_tblTranscript_dict = []
	# om ?p=X är större än faktiskt antal sidor
	if page_GET is not None and page_GET > len(item_tblImage_dict):
		return redirect("/letter?id=" + GET_id + "&p=1")


	print("#################")
	print("#################")
	print("#################")
	print("#################")
	print("#################")
	print(item_tblTranscript_dict)
	print(item_tblImage_dict)
	print(response_SELECT_tblTranscript)

#	item_tblImage_dict[page_GET]
#	image_info = [image_name, page_number]


	return render_template('letter.html', item_tblMaster_dict = item_tblMaster_dict, debug=debug, item_tblItem_dict=item_tblItem_dict, item_tblReference_dict=item_tblReference_dict,item_tblInHandOf_dict=item_tblInHandOf_dict, link=link, item_tblImage_dict=item_tblImage_dict, page=page_GET,item_tblTranscript_dict=item_tblTranscript_dict)

@app.route('/images/<filename>')
def uploaded_file(filename):
	print(1)
	return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

#todo                   ***********************************
#todo				************ SUBMIT ***************
#todo				   ***********************************

@app.route('/submit/', methods=['POST', 'GET'])
def upload_letter():
	### Initializing vars
	sender_INSERT_status = ['','','','','']
	addressee_INSERT_status = ['','','','','']
#	error_message = ''
	debug = ''
	# Checks if POST request
	if request.method == "POST":
		db_tblMaster_columns = ["pk_WCP_Number","TempNumber","ParentRecordType","fk_PersonID_Author","AuthorInferred","AuthorUncertain",
								"fk_AddressID_Author","AuthorsAddressInferred","AuthorsAddressUncertain","fk_PersonID_Addressee","AddresseeInferred",
								"AddresseeUncertain","fk_AddressID_Addressee","AddresseesAddressInferred","AddresseesAddressUncertain","Day","DayInferred",
								"DayUncertain","Month","MonthInferred","MonthUncertain","Year","YearInferred","YearUncertain","NotesLetterDate","Summary",
								"ScrutinySumm","fk_EditorID_RecordCreator","RecordDate","HideRecord"]

		# GET ID:s of people involved!
	# Sender variables
		sender_title = str(request.form['sender_title']).encode('utf-8')
		sender_forename = str(request.form['sender_forename']).encode('utf-8')
		sender_surname = str(request.form['sender_surname']).encode('utf-8')
		sender_address = str(request.form['sender_address']).encode('utf-8')
	# Recipient variables
		recipient_title = str(request.form['recipient_title']).encode('utf-8')
		recipient_forename = str(request.form['recipient_forename']).encode('utf-8')
		recipient_surname = str(request.form['recipient_surname']).encode('utf-8')
		recipient_address = str(request.form['recipient_address']).encode('utf-8')

		if len(sender_surname) > 0 or len(sender_forename) > 0:
		# SELECT ID of sender (if exists)
			fk_PersonID_sender = query_db("SELECT pk_PersonID FROM tblPerson WHERE Forenames LIKE '%" + sender_forename + "%' AND Surname LIKE '%" + sender_surname + "%'")
			if len(fk_PersonID_sender) != 0:
				fk_PersonID_sender = fk_PersonID_sender[0][0]  # removes formatting todo: unclear origin of messed up types

		# If sender does not exist in tblPerson, we create a new tblPerson record of the addressee!
					# Ugly hack... we don't want to create a new person if sender-title/forename/surname/address are all blank
			elif len(fk_PersonID_sender) == 0 and (sender_forename != "" or sender_surname !=""):
				response_sender = query_db("INSERT INTO tblPerson (Title, Forenames, Surname) VALUES (?,?,?)",[sender_title,sender_forename,sender_surname])
			# Get ID of inserted person (sender)
				fk_PersonID_sender = query_db("SELECT pk_PersonID FROM tblPerson WHERE Title = ? AND Forenames = ? AND Surname = ?",[sender_title,sender_forename,sender_surname])
				fk_PersonID_sender = fk_PersonID_sender[0][0]  # removes formatting todo: unclear origin of messed up types

				sender_INSERT_status = ['True',sender_title,sender_forename,sender_surname,fk_PersonID_sender]
		else:
			fk_PersonID_sender = 'NULL'

	# SELECT ID of addressee (if exists
		if len(recipient_forename) > 0 or len(recipient_surname) > 0:
			fk_PersonID_Addressee = query_db("SELECT pk_PersonID FROM tblPerson WHERE Forenames LIKE '%" + recipient_forename + "%' AND Surname LIKE '%" + recipient_surname + "%'")
			if len(fk_PersonID_Addressee) != 0:
				fk_PersonID_Addressee = fk_PersonID_Addressee[0][0]  # removes formatting todo: unclear origin of messed up types

		# If addresse does not exist in tblPerson, we create a new tblPerson record of the addressee!
			# Ugly hack... we don't want to create a new person if addressee-title/forename/surname/address are all blank
			elif len(fk_PersonID_Addressee) == 0 and (recipient_forename != "" or recipient_surname != ""):
				reseponse_addressee = query_db("INSERT INTO tblPerson (Title, Forenames, Surname) VALUES (?,?,?)", [recipient_title,recipient_forename,recipient_surname])
			# Get ID of insterted person (addressee)
				fk_PersonID_Addressee = query_db("SELECT pk_PersonID FROM tblPerson WHERE Title = ? AND Forenames = ? AND Surname = ?", [recipient_title,recipient_forename,recipient_surname])
				fk_PersonID_Addressee = fk_PersonID_Addressee[0][0]  # removes formatting todo: unclear origin of messed up types
				addressee_INSERT_status = ['True',recipient_title,recipient_forename,recipient_surname,fk_PersonID_Addressee]
		else:
			fk_PersonID_Addressee = 'NULL'


		if fk_PersonID_Addressee == 'NULL' and fk_PersonID_sender == 'NULL':
			error_message = "Both sender and recipient may not be left blank"
			return render_template('submit.html', error_message=error_message)

#			debug = ["addressee", fk_PersonID_Addressee, type(fk_PersonID_Addressee), "sender", fk_PersonID_sender]

# Någon funktion: om ej ID finns, skapa nytt!!!!


# INSERT record into tblMaster
		sender_address = str(sender_address)

		recipient_address = str(recipient_address)
# Populate column entries for INSERT INTO tblMaster

		#pk_WCP_Number 					= "" - auto-incremented!
		TempNumber 						= "" 																# Done. N/A?
		ParentRecordType 				= "" 																# Done. N/A?
		fk_PersonID_Author 				= str(fk_PersonID_sender)											#
		AuthorInferred 					= str(request.form['sender_inferred']) 								# Done. Todo: validity check (T/F)+ implement in letter output
		AuthorUncertain 				= str(request.form['sender_uncertain'])								# Done. Todo: validity check (T/F) + implement in letter output
		fk_AddressID_Author				= "" 																#
		AuthorsAddressInferred 			= str(request.form['sender_address_inferred']) 						# Done. Todo: validity check (T/F) + implement in letter output
		AuthorsAddressUncertain 		= str(request.form['sender_address_uncertain']) 					# Done. Todo: validity check (T/F) + implement in letter output

		fk_PersonID_Addressee 			= str(fk_PersonID_Addressee)										#
		AddresseeInferred 				= str(request.form['recipient_inferred']) 							# Done. Todo: validity check (T/F) + implement in letter output
		AddresseeUncertain				= str(request.form['recipient_uncertain']) 							# Done. Todo: validity check + implement in letter output
		fk_AddressID_Addressee 			= "" 																#
		AddresseesAddressInferred 		= str(request.form['recipient_address_inferred']) 					# Done. Todo: validity check (T/F) + implement in letter output
		AddresseesAddressUncertain 		= str(request.form['recipient_address_uncertain'])					# Done. Todo: validity check (T/F) + implement in letter output
		Day 							= str(request.form['day'])											# Done. Todo: implement validity check
		DayInferred 					= str(request.form['day_inferred'])									# Done. Todo: implement in letter output
		DayUncertain					= str(request.form['day_uncertain']) 								# Done. Todo: implement in letter output
		Month							= str(request.form['month'])										# Done. Todo: implement validity check. Also, output str, not int.
		MonthInferred					= str(request.form['month_inferred'])								# Done. Todo: implement in letter output
		MonthUncertain					= str(request.form['month_uncertain']) 								# Done. Todo: implement in letter output
		Year							= str(request.form['year'])											# Done. Todo: implement validity check
		YearInferred					= str(request.form['year_inferred']) 								# Done. Todo: implement in letter output
		YearUncertain					= str(request.form['year_uncertain']) 								# Done. Todo: implement in letter output
		NotesLetterDate					= str(request.form['date_notes']).encode('utf-8')					# Done.
		Summary							= str(request.form['summary']) 										# Done. Todo: does not display in letter view ...
		ScrutinySumm					= "0" 																# Done. Todo: implement option for OTHER USERS in edit menu
		fk_EditorID_RecordCreator		= "1" 																# Done. ID of user that created record. ToDo change to actual user ID; once users implemented
																											#       semi-implemented (var fk_EditorID_RecordCreator) set to 1. Todo: implement users!
		RecordDate						= str(datetime.datetime.now().isoformat()) 							# Done. Todo: trancate date.
		#HideRecord, messy due to usage of HTML button. Todo if CBA.
		try:
			HideRecord = str(request.form['hide_letter'])
			HideRecord = "1"
		except:
			# Exceotion if Hide Letter button is not clicked (no such POST paramenter => NoneType => Exception raised!)
			HideRecord = "0"

		query_db("INSERT INTO tblMaster (\
										TempNumber, ParentRecordType, fk_PersonID_Author, AuthorInferred,\
										AuthorUncertain, fk_AddressID_Author, AuthorsAddressInferred, AuthorsAddressUncertain,\
										fk_PersonID_Addressee, AddresseeInferred, AddresseeUncertain, fk_AddressID_Addressee,\
										AddresseesAddressInferred, AddresseesAddressUncertain, Day, DayInferred, DayUncertain, \
										Month, MonthInferred, MonthUncertain, Year, YearInferred, YearUncertain, NotesLetterDate,\
										Summary, ScrutinySumm, fk_EditorID_RecordCreator, RecordDate, HideRecord) \
										VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",\
										[TempNumber, ParentRecordType, fk_PersonID_Author, AuthorInferred,
										AuthorUncertain, fk_AddressID_Author, AuthorsAddressInferred, AuthorsAddressUncertain,
										fk_PersonID_Addressee, AddresseeInferred, AddresseeUncertain, fk_AddressID_Addressee,
										AddresseesAddressInferred, AddresseesAddressUncertain, Day, DayInferred, DayUncertain,
										Month, MonthInferred, MonthUncertain, Year, YearInferred, YearUncertain, NotesLetterDate,
										Summary, ScrutinySumm, fk_EditorID_RecordCreator, RecordDate, HideRecord])

# Fetch new record ID (pk_WCP_Number) by SELECT-ing for latest pk_ID
		pk_WCP_Number = query_db("SELECT pk_WCP_Number from tblMaster WHERE RecordDate = ?", [RecordDate])
		pk_WCP_Number = pk_WCP_Number[0][0]
		###################################
	  ### INSERT record into tblItem  ###
		###################################
#### Note: tblItem contains detailed information of record with pk_WCP_Number
# Schema for tblItem. Used (later) to populate list with column entries of tblItem.
	#### Todo: db_tblItem_columns kanske inte behövs om endast INSERT INTO (och inte SELECT * FROM) ...
		db_tblItem_columns = ["pk_ItemID","fk_WCP_Number","fk_ItemTypeID","fk_ProvenanceID","FindingNo","ItemDescription",
							"ItemNotes","fk_ReferenceID","PagePublished","PubNotes","TotalPages","TextPages",
							"fk_LetterTypeID","fk_TextTypeID","fk_InHandOfID","fk_SignedByID","fk_CopyTypeID","fk_TextConditionID",
							"Language","PhysDescInfo","fk_PersonID_Copyright","fk_CopyrightID","fk_ProvenanceID_CopyrightHolder",
							"HideImages","TranscriptFileName","fk_EditorID_Transcriber","TranscriptionDate","ScrutinyTrans",
							"fk_EditorID_SignedOff","DateSignedOff","HideTranscript","ScrutinyRecord","fk_EditorID_RecordCreator","RecordDate"]


		# Creation of tblItem record. Prepare strings for INSERT INTO tblItem.
		# pk_ItemID = "" - auto-incremented!
		fk_WCP_Number					= pk_WCP_Number									# Done. fk of tblItem to point to pk of tblMaster
		fk_ItemTypeID					= ""											# Item type ID. Arbitrary default set to 1, only dealing with letters for now
		fk_ProvenanceID					= "1"											# arbitrary default, todo: unclear function
		FindingNo						= None											# Unclear what FindingNo is. Todo
		ItemDescription					= ""											# Description of item. Todo form
		ItemNotes						= ""											# Notes on item. Todo form
		fk_ReferenceID					= ""											# ID of reference. TOdo use SQL
		PagePublished					= ""											# Todo: unclear (T/F?)
		PubNotes						= ""											# Notes on if published
		TotalPages						= ""											# Total pages of item. Todo: By counting images?
		TextPages						= ""											# unclear field
		fk_LetterTypeID					= ""											# See associated table, db_tblLetterType_columns = ["pk_LetterTypeID", "LetterType","SortOrder"]
		fk_TextTypeID					= ""											# Unclear field
		fk_InHandOfID					= ""											# ID of owner. Todo implement! db_tblInHandOf_columns = ["pk_InHandOfID", "InHandOf"]
		fk_SignedByID					= ""											#
		fk_CopyTypeID					= ""											#
		fk_TextConditionID				= ""											#
		Language 						= str(request.form['language']) 				# Done. Todo: does not display in letter view!
		PhysDescInfo					= ""											#
		fk_PersonID_Copyright			= ""											#
		fk_CopyrightID					= ""											# db_tblCopyrightStatus_columns = ["pk_CopyrightID","CopyrightStatus","SortOrder"]
		fk_ProvenanceID_CopyrightHolder = ""											#
		#HideImages						= ''#str(request.form['hide_images'])			# Done. Omständligt ty default unclicked button jävlas... Todo: Ensure 0/1 or T/F.
		try:
			HideImages = str(request.form['hide_images'])
			HideImages = "1"
		except:
			# Exception if HideImage button is not clicked (no such POST paramenter => NoneType => Exception raised!)
			HideImages = "0"
		TranscriptFileName				= str(request.form['transcript'])				# Done. TranscriptFileName contains actual transcript, unclear where else to story.
		fk_EditorID_Transcriber			= "1"											# Done. Todo: implement users!
		TranscriptionDate				= str(datetime.datetime.now().isoformat())		# Done. Todo: trancate date.= str(datetime.datetime.now().isoformat()) # Todo: trancate date.
		ScrutinyTrans					= ""											#
		fk_EditorID_SignedOff			= ""											#
		DateSignedOff					= ""											#
		#HideTranscript					= str(request.form['hide_transcript'])			# Done. Omständligt ty default unclicked button jävlas... Todo: ensure 0/1 or T/F.
		try:
			HideTranscript = str(request.form['hide_transcript'])
			HideTranscript = "1"
		except:
			# Exception if HideImage button is not clicked (no such POST paramenter => NoneType => Exception raised!)
			HideTranscript = "0"
		ScrutinyRecord					= "0"											# Done. Todo: Implementera i edit view!
		fk_EditorID_RecordCreator		= "1"											# Done. Todo: implement users!
		RecordDate						= ""											#
		PagePublished = ''

		query_db("INSERT INTO tblItem (\
										fk_WCP_Number, fk_ItemTypeID, fk_ProvenanceID, FindingNo,\
										ItemDescription, ItemNotes, fk_ReferenceID, PagePublished, PubNotes,\
										TotalPages, TextPages, fk_LetterTypeID, fk_TextTypeID, fk_InHandOfID,\
										fk_SignedByID, fk_CopyTypeID, fk_TextConditionID, Language, PhysDescInfo,\
										fk_PersonID_Copyright, fk_CopyrightID, fk_ProvenanceID_CopyrightHolder,\
										HideImages, TranscriptFileName, fk_EditorID_Transcriber, TranscriptionDate,\
										ScrutinyTrans, fk_EditorID_SignedOff, DateSignedOff, HideTranscript,\
										ScrutinyRecord, fk_EditorID_RecordCreator, RecordDate)\
									VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
										[fk_WCP_Number, fk_ItemTypeID, fk_ProvenanceID, FindingNo,
										ItemDescription, ItemNotes, fk_ReferenceID, PagePublished, PubNotes,
										TotalPages, TextPages, fk_LetterTypeID, fk_TextTypeID, fk_InHandOfID,
										fk_SignedByID, fk_CopyTypeID, fk_TextConditionID, Language, PhysDescInfo,
										fk_PersonID_Copyright, fk_CopyrightID, fk_ProvenanceID_CopyrightHolder,
										HideImages, TranscriptFileName, fk_EditorID_Transcriber, TranscriptionDate,
										ScrutinyTrans, fk_EditorID_SignedOff, DateSignedOff, HideTranscript,
										ScrutinyRecord, fk_EditorID_RecordCreator, RecordDate])

		# Fetch new record ID (pk_ItemID) by SELECT-ing for latest pk_ItemID
		pk_ItemID = query_db("SELECT pk_ItemID from tblItem WHERE fk_WCP_Number = ?", [pk_WCP_Number])
		pk_ItemID = pk_ItemID[0][0]

		db_tblReference_columns = ["pk_ReferenceID","Authors","YearPrinted","YearPublished","Title","Website","WebsiteURL", "DateAccessed","Publication",
									"Series","Volume","Part","PageRange","InAuthor","BookTitle","Publisher","BookPages","NotesRef","TempPageCited"]

#pk_LetterTypeID, (tblLetterType) pk_InHandOfID (tblTextType), pk_Reference_ID (tblReference)

#				items = query_db("SELECT * from tblItem WHERE fk_WCP_Number = '" + GET_id + "'")
#				items_table = []
#				items_dict = {}
#				for item in items:
#						for column_name in db_tblItem_columns:
#								items_dict[column_name] = items[items.index(item)][db_tblItem_columns.index(column_name)]
#						items_table.append(items_dict)
#						items_dict = {}

		###################################
		### INSERT record into tblImage  ###
		###################################
		db_tblImage_columns = ["pk_ImageID", "fk_ItemID", "ImageFileName", "SortNo", "PageNo"]

		uploaded_images = request.files.getlist("img")

		for image in uploaded_images:
			if image and allowed_file(image.filename):
				image_name = secure_filename(image.filename)
				ImageFieldName = str(pk_WCP_Number) + "_" + str(pk_ItemID) + "_" + str(image_name)
				image.save(os.path.join(app.config['UPLOAD_FOLDER'],ImageFieldName))

				# removal of file extension from image_name
				image_name = image_name.rsplit('.',1)
				image_name = str(image_name[0])
				PageNo = image_name

				query_db("INSERT INTO tblImage (\
											fk_ItemID,ImageFileName,PageNo)\
					 VALUES (?,?,?)",
					[pk_ItemID,ImageFieldName,PageNo])


		# Create item table type
		submit_success = True
		entry_id = pk_WCP_Number
		return render_template('submit.html', success = submit_success, entry_id = entry_id, debug=debug, sender_INSERT_status=sender_INSERT_status, addressee_INSERT_status=addressee_INSERT_status)

#		return redirect("/", code=302)
	# Om ej POST request, utan en GET request
	else:
		GET_sender_ID = request.args.get('from')
		GET_addressee_ID = request.args.get('to')

		if GET_sender_ID is not None:
			author = query_db("SELECT pk_PersonID,Title,Forenames,Surname FROM tblPerson WHERE pk_PersonID = ?",[GET_sender_ID])
			author = author[0] # Removes SQL-formatting
		else:
			author = ''
		if GET_addressee_ID is not None:
			addressee = query_db("SELECT pk_PersonID,Title,Forenames,Surname FROM tblPerson WHERE pk_PersonID = ?",[GET_addressee_ID])
			addressee = addressee[0] # Removes SQL-formatting
		else:
			addressee = ''

#		GET_from = GET_to = ""
#		if GET_from is None:
#			GET_from = ""
#		if GET_to is None:
#			GET_to = ""
#				return render_template('submit.html', GET_from = GET_from, GET_to = GET_to)

		return render_template('submit.html', author=author, addressee=addressee)

@app.route('/person/')
def return_person():
	GET_id = request.args.get('id').encode('utf8')
	GET_id = filter(lambda x: x.isdigit(), GET_id)  # only allows int (SQL-filter)


	# Get contents of master table
	db_tblPerson_columns = ["pk_PersonID", "Surname", "Forenames", "FullNameTemp", "Title", "BirthDate",
							"DeathDate", "Biography","NotesPerson", "ScrutinyBiog", "CopyrightHolder",
	 						"CopyrightCreditLine", "Permission", "NotesCopyright"]

	item_head = query_db("SELECT * from tblPerson WHERE pk_PersonID = ?", [GET_id])  # SQL-query: parametrized


	item_head_dict = {}
	for column_name in db_tblPerson_columns:
		item_head_dict[column_name] = item_head[0][db_tblPerson_columns.index(column_name)]
	person_dict = item_head_dict

	# Get letters sent by id from tblMaster
	letters_sent_head = query_db("SELECT * from tblMaster WHERE pk_WCP_Number = ?", [GET_id])  # SQL-query: parametrized
	db_tblMaster_columns = ["pk_WCP_Number", "TempNumber", "ParentRecordType", "fk_PersonID_Author", "AuthorInferred",
							"AuthorUncertain",
							"fk_AddressID_Author", "AuthorsAddressInferred", "AuthorsAddressUncertain",
							"fk_PersonID_Addressee", "AddresseeInferred",
							"AddresseeUncertain", "fk_AddressID_Addressee", "AddresseesAddressInferred",
							"AddresseesAddressUncertain", "Day", "DayInferred",
							"DayUncertain", "Month", "MonthInferred", "MonthUncertain", "Year", "YearInferred",
							"YearUncertain", "NotesLetterDate", "Summary",
							"ScrutinySumm", "fk_EditorID_RecordCreator", "RecordDate", "HideRecord"]
	letters_sent_dict = {}
	for column_name in db_tblMaster_columns:
		letters_sent_dict[column_name] = letters_sent_head[0][db_tblMaster_columns.index(column_name)]

#	items_table = []
#	items_dict = {}
#	for item in items:
#
#		for column_name in db_tblItem_columns:
#			items_dict[column_name] = items[items.index(item)][db_tblItem_columns.index(column_name)]
#		items_table.append(items_dict)
#		items_dict = {}

	# Get letters received by id

	return render_template('person.html', person_dict=person_dict, letters_sent_dict=letters_sent_dict)

# item_head_dict -> person_dict
# items_table -> letters_sent_dict
#################

@app.route('/letter_edit/', methods=['POST', 'GET'])
def letter_edit():

	GET_id = request.args.get('id').encode('utf8')
	GET_id = filter(lambda x: x.isdigit(), GET_id)		#only allows int (SQL-filter)
	db_tblMaster_columns = ["pk_WCP_Number","TempNumber","ParentRecordType","fk_PersonID_Author","AuthorInferred","AuthorUncertain",
							"fk_AddressID_Author","AuthorsAddressInferred","AuthorsAddressUncertain","fk_PersonID_Addressee","AddresseeInferred",
							"AddresseeUncertain","fk_AddressID_Addressee","AddresseesAddressInferred","AddresseesAddressUncertain","Day","DayInferred",
							"DayUncertain","Month","MonthInferred","MonthUncertain","Year","YearInferred","YearUncertain","NotesLetterDate","Summary",
							"ScrutinySumm","fk_EditorID_RecordCreator","RecordDate","HideRecord"]

	db_tblItem_columns = ["pk_ItemID","fk_WCP_Number","fk_ItemTypeID","fk_ProvenanceID","FindingNo","ItemDescription",
			"ItemNotes","fk_ReferenceID","PagePublished","PubNotes","TotalPages","TextPages",
			"fk_LetterTypeID","fk_TextTypeID","fk_InHandOfID","fk_SignedByID","fk_CopyTypeID","fk_TextConditionID",
			"Language","PhysDescInfo","fk_PersonID_Copyright","fk_CopyrightID","fk_ProvenanceID_CopyrightHolder",
			"HideImages","TranscriptFileName","fk_EditorID_Transcriber","TranscriptionDate","ScrutinyTrans",
			"fk_EditorID_SignedOff","DateSignedOff","HideTranscript","ScrutinyRecord","fk_EditorID_RecordCreator","RecordDate"]
	db_tblReference_columns = ["pk_ReferenceID", "Authors", "YearPrinted", "YearPublished", "Title", "Website",
							   "WebsiteURL", "DateAccessed", "Publication", "Series", "Volume", "Part", "PageRange",
							   "InAuthor", "BookTitle", "Publisher", "BookPages", "NotesRef", "TempPageCited"]
	db_tblInHandOf_columns = ["pk_InHandOfID","InHandOf","collection","InHandOfDocumentID"]

	dict = []
	if request.method == "POST":
		return render_template('letter.html', message="Letter updated")
	if request.method == "GET":
		# Here we are SELECT-ing information from DB, and displaying it in the submit form
		# Basically copy-paste from submit form.
		# tblMaster
		item_tblMaster_dict = {}
		response_SELECT_tblMaster = query_db("SELECT * from tblMaster WHERE pk_WCP_Number = ?", [GET_id])
		for column_name in db_tblMaster_columns:
			item_tblMaster_dict[column_name] = response_SELECT_tblMaster[0][db_tblMaster_columns.index(column_name)]

		# tblItem
		fk_WCP_Number = item_tblMaster_dict['pk_WCP_Number']
		item_tblItem_dict = {}
		response_SELECT_tblItem = query_db("SELECT * from tblItem WHERE fk_WCP_Number = ?", [fk_WCP_Number])
		for column_name in db_tblItem_columns:
			item_tblItem_dict[column_name] = response_SELECT_tblItem[0][db_tblItem_columns.index(column_name)]

		# tblReference
		item_tblReference_dict = {}
		response_SELECT_tblReference = query_db("SELECT * from tblReference WHERE pk_ReferenceID = ?",[item_tblItem_dict['fk_ReferenceID']])
		for column_name in db_tblReference_columns:
			if len(response_SELECT_tblReference) > 1:
				item_tblReference_dict[column_name] = response_SELECT_tblReference[0][db_tblReference_columns.index(column_name)]
			else:  # len() = 0 if no edition (reference) available.
				item_tblReference_dict[column_name] = ''

		# tblInHandOf
		item_tblInHandOf_dict = {}
		response_SELECT_tblInHandOf = query_db("SELECT * FROM tblInHandOf tblInHandOf WHERE pk_InHandOfID = ?",[item_tblItem_dict['fk_InHandOfID']])
		for column_name in db_tblInHandOf_columns:
			if len(response_SELECT_tblInHandOf) > 1:
				item_tblInHandOf_dict[column_name] = response_SELECT_tblInHandOf[0][
					db_tblInHandOf_columns.index(column_name)]
			else:
				item_tblInHandOf_dict[column_name] = ''

		# tblImage
		item_tblImage_dict = []
		response_SELECT_tblImage = query_db("SELECT ImageFileName,PageNo from tblImage WHERE fk_ItemID = ?",[item_tblItem_dict['pk_ItemID']])
		for row in response_SELECT_tblImage:
			ImageFileName = row[0]
			PageNo = row[1]
			item_tblImage_dict.append([ImageFileName, PageNo])

		# Author and addressee information
		sender_ID = item_tblMaster_dict['fk_PersonID_Author']
		addressee_ID = item_tblMaster_dict['fk_PersonID_Addressee']

		if str(sender_ID) != "NULL":
			author = query_db("SELECT pk_PersonID,Title,Forenames,Surname FROM tblPerson WHERE pk_PersonID = ?",[sender_ID])
			author = author[0] # Removes SQL-formatting
		else:
			author = ''
		if str(addressee_ID) != "NULL":
			addressee = query_db("SELECT pk_PersonID,Title,Forenames,Surname FROM tblPerson WHERE pk_PersonID = ?",[addressee_ID])
			addressee = addressee[0] # Removes SQL-formatting
		else:
			addressee = ''

		return render_template('letter_edit.html', item_tblMaster_dict=item_tblMaster_dict,item_tblItem_dict=item_tblItem_dict,item_tblReference_dict=item_tblReference_dict,item_tblInHandOf_dict=item_tblInHandOf_dict,item_tblImage_dict=item_tblImage_dict,author=author,addressee=addressee)

if __name__ == "__main__":
	app.run(host='0.0.0.0')
