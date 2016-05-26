import MySQLdb
from sets import Set
from collections import defaultdict
import re
from datetime import datetime
from datetime import date
from datetime import timedelta
from dateutil.easter import easter
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta as rd
from dateutil.relativedelta import MO, TH, FR
from sklearn import decomposition
from sklearn import linear_model
from sklearn import svm
from sklearn import ensemble
from scipy import stats
import numpy.random as nr
import numpy
from sklearn import svm
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFECV
import matplotlib.pyplot as plt
from holidays import Holidays
import pickle

####### IGNORE THESE FUNCTIONS

def actualTime(w, last, first, qc_holidays):
	# remove weekends
	total_time = (w[last]-w[first]).total_seconds()/float(60*60*24)
	# print "Before: " + str(total_time)
	t_0 = w[first]
	t_5 = w[last]
	to_subtract = 0
	while (t_0 < t_5):
		if (t_0.weekday()==5 or t_0.weekday()==6 or (t_0.date() in qc_holidays)):
			to_subtract += 1
		t_0 += timedelta(days=1)

	total_time = total_time - float(to_subtract)
	if (total_time < 0):
		total_time = 0.0

	return total_time

def addWithWeekends(initialTime, predictedDays, qc_holidays):
	final_time = initialTime + timedelta(days=predictedDays)
	while (initialTime < final_time):
		if (initialTime.weekday()==5 or initialTime.weekday()==6 or (initialTime.date() in qc_holidays)):
			final_time += timedelta(days=1)
		initialTime += timedelta(days=1)

	return final_time

def printPatient(arr, of, timelines):
	of.write("-----\n")
	of.write("AliasName" + "\t" + "PatientSerNum" + "\t" + "CreationDate" + "\t" + "Status" + "\n")

	for line in arr:
		of.write(str(line["AliasName"]) + "\t" + str(line["PatientSerNum"]) + "\t" + str(line["CreationDate"]) + "\t" + str(line["Status"]))
		for timeline in timelines:
			of.write("\t")
			for dt in timeline:
				if dt == line["CreationDate"]:
					of.write("=====")
		of.write("\n")

	of.write("-----\n\n")

def timelineActive(arr, time):
	toRet = False
	toBreak = False
	for i in range(len(arr)):
		if arr[i]['AliasName'] == "READY FOR MD CONTOUR":
			for j in range(i, len(arr)):
				if arr[i]['AliasName'] == "READY FOR TREATMENT":
					if arr[i]['CreationDate'] < time and arr[j]['CreationDate'] > time:
						toRet = True
						toBreak = True
						break

			if toBreak == True:
				break

	return toRet

#######


# findNext takes as input a table, a query string, 
# a range of values in the table to iterate over, 
# and a status code, and simply returns an array of all the numbers 
# i within the valid range for which the table[i] 
# has the designated query string and status code.

def findNext(arr, nextString, iterStart, iterEnd, status):
	l = []
	if status==0:		
		for i in range(iterStart, iterEnd):
			if arr[i]['AliasName'] == nextString:
				l.append(i)
	elif status==1:
		for i in range(iterStart, iterEnd):
			if arr[i]['AliasName'] == nextString and arr[i]['Status']=='Open':
				l.append(i)
	elif status==2:
		for i in range(iterStart, iterEnd):
			if arr[i]['AliasName'] == nextString and arr[i]['Status']=='In Progress':
				l.append(i)
	elif status==3:
		for i in range(iterStart, iterEnd):
			if arr[i]['AliasName'] == nextString and arr[i]['Status']=='Completed':
				l.append(i)		
	elif status==4:
		for i in range(iterStart, iterEnd):
			if arr[i]['AliasName'] == nextString and arr[i]['Status']=='Manually Completed':
				l.append(i)			
	else:
		print "invalid status" # do nothing

	# return list of next positions
	return l

# notTermPresent takes as input the same things as findNext, 
# except it returns 1 if the query string/status code is in the valid range, and 0 otherwise. 
def notTermPresent(arr, notString, start, end, status):
	if status==0:
		for i in range(start, end):
			if arr[i]['AliasName']==notString:
				return 1
	elif status==1:
		for i in range(start, end):
			if arr[i]['AliasName']==notString and arr[i]['Status']=='Open':
				return 1
	elif status==2:
		for i in range(start, end):
			if arr[i]['AliasName']==notString and arr[i]['Status']=='In Progress':
				return 1
	elif status==3:
		for i in range(start, end):
			if arr[i]['AliasName']==notString and arr[i]['Status']=='Completed':
				return 1
	elif status==4:
		for i in range(start, end):
			if arr[i]['AliasName']==notString and arr[i]['Status']=='Manually Completed':
				return 1
	else:
		print "invalid status" # do nothing		

	return 0

# for details, see the oncotime report Laurie sent - this function just takes as input an array that has 
# all the events for a patient in chronological order, as well as a sequence of events to match, and
# returns an array of arrays (of INDICES into the original arr array), where each array
# represents a valid sequence of events for that patient that matches the sequence specifier
def findAll(arr, sequence, not_array, status_array, endCurPatient, l):
	if (len(sequence)==0):
		return l # return [8]

	ret = []

	if not_array[0] == 1: # not simpleExp or functionExp
		newseq =  sequence[:]
		to_check = newseq.pop(0)
		new_not = not_array[:]
		new_not.pop(0)
		new_stat = status_array[:]
		new_stat.pop(0)

		a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)	
		for seq in a:
			if notTermPresent(arr, to_check, seq[0]+1, seq[1], status_array[0])==0:
				ret.append(seq)
	elif not_array[0] == 2: # brace/pipe
		# same if len(l) == 0
		for bracei in range(len(sequence[0])):
			# print braceTerm
			newseq = sequence[:]
			newseq.pop(0)
			newseq.insert(0, sequence[0][bracei])
			new_not = not_array[:]
			new_not.pop(0)
			new_not.insert(0,0)
			new_stat = status_array[:]

			stat_term = new_stat.pop(0)
			new_stat.insert(0, stat_term[bracei])

			a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)
			for seq in a:
				ret.append(seq)	

		# for braceTerm in sequence[0]:
		# 	# print braceTerm
		# 	newseq = sequence[:]
		# 	newseq.pop(0)
		# 	newseq.insert(0, braceTerm)
		# 	new_not = not_array[:]
		# 	new_not.pop(0)
		# 	new_not.insert(0,0)
		# 	new_stat = status_array[:]

		# 	a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)
		# 	for seq in a:
		# 		ret.append(seq)
	elif not_array[0] == 3: # bracestar
		for i in range(len(l)):
			newseq = sequence[:]
			newseq.pop(0)
			new_not = not_array[:]
			new_not.pop(0)
			new_stat = status_array[:]
			new_stat.pop(0)

			a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)
			# print "a: " + str(a)
			for seq in a:
				nextPos = seq[1]
				nar = []
				for bracei in range(len(sequence[0])):
					newl = findNext(arr, sequence[0][bracei], l[i]+1, nextPos, status_array[0][bracei])
					# print "newl: " + str(newl)
					for num in newl:
						nar.append(num)

				# for braceTerm in sequence[0]:
				# 	newl = findNext(arr, braceTerm, l[i], nextPos, status_array[0])
				# 	# print "newl: " + str(newl)
				# 	for num in newl:
				# 		nar.append(num)

				if l[i] < nextPos:
					nar.sort()
					newarr = [l[i]] + nar
					newarr = newarr + seq[1:len(seq)]
					# print "newarr: " + str(newarr)
					ret.append(newarr)
	elif not_array[0] == 4: # star
		if len(l)==0:
			l = []
			for i in range(endCurPatient):
				l.append(i)
			sequence.pop(0)
			not_array.pop(0)
			status_array.pop(0)
			return findAll(arr, sequence, not_array, status_array, endCurPatient, l)

		for i in range(len(l)):
			newseq = sequence[:]
			newseq.pop(0)
			new_not = not_array[:]
			new_not.pop(0)
			new_stat = status_array[:]
			new_stat.pop(0)

			a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)

			for seq in a:
				second = seq[1]
				nar = []

				if l[i] < second:
					for j in range(l[i]+1, second):
						newarr = [l[i]] + [j] + seq[1:len(seq)]
						ret.append(newarr)
	elif not_array[0] == 5: # not brace/pipe/bracestar
		newseq =  sequence[:]
		to_check = newseq.pop(0)
		new_not = not_array[:]
		new_not.pop(0)
		new_stat = status_array[:]
		to_check_stat = new_stat.pop(0)

		a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)	
		for seq in a:
			flag = 0

			for bracei in range(len(to_check)):
				if notTermPresent(arr, to_check[bracei], seq[0]+1, seq[1], to_check_stat[bracei])==1:
					flag = 1
					break

			# for braceTerm in to_check:
			# 	if notTermPresent(arr, braceTerm, seq[0]+1, seq[1], status_array[0])==1:
			# 		flag = 1
			# 		break

			if flag == 0:		
				ret.append(seq)
	elif not_array[0] == 6: # not star
		newseq =  sequence[:]
		to_check = newseq.pop(0)
		new_not = not_array[:]
		new_not.pop(0)
		new_stat = status_array[:]
		new_stat.pop(0)

		a = findAll(arr, newseq, new_not, new_stat, endCurPatient, l)	
		for seq in a:
			if seq[1]==seq[0]+1:
				ret.append(seq)
	else: # normal
		if len(l)==0:
			l = findNext(arr, sequence[0], 0, len(arr), status_array[0])
			sequence.pop(0)
			status_array.pop(0)
			not_array.pop(0)
			if len(l)==0:
				return []
			else:
				return findAll(arr, sequence, not_array, status_array, endCurPatient, l)

		for i in range(len(l)):
			newl = findNext(arr, sequence[0], l[i]+1, endCurPatient, status_array[0]) #[6] #[8]
			# print "newl: " + str(newl)

			if len(newl)!=0:
				newseq = sequence[:]
				newseq.pop(0) # [ready_for_md_contour] []
				new_not = not_array[:]
				new_not.pop(0)
				new_stat = status_array[:]
				new_stat.pop(0)

				a = findAll(arr, newseq, new_not, new_stat, endCurPatient, newl) # a= [6,8]
				# print "a: " + str(a)

				if len(a) > 0:
					if isinstance(a[0], int):
						# print "a: " + str(a)
						for n in a:
							nar = []
							nar.append(l[i])
							nar.append(n)
							ret.append(nar)
					else:
						for seq in a:
							seq.insert(0, l[i]) 
							ret.append(seq)

	# print "ret: " + str(ret)
	return ret 

def main():
	print "Done Loading Libraries"
	mysql_cn = MySQLdb.connect(host='localhost', port=3306, user='alvin', passwd='', db='hig')
	sequenceCursor = mysql_cn.cursor(MySQLdb.cursors.DictCursor)
	

	# query mysql for all the tasks, appointments, plans, etc for every patient (with serNum < 35384)

	sequenceCursor.execute("""
    SELECT a.AliasName, t.PatientSerNum, t.CreationDate, t.CompletionDate, t.Status
    FROM Task t INNER JOIN Patient p ON p.PatientSerNum = t.PatientSerNum 
        INNER JOIN Alias a ON a.AliasSerNum = t.AliasSerNum 
    WHERE p.PatientSerNum<35384
    UNION ALL 
    SELECT a.AliasName, ap.PatientserNum, ap.ScheduledStartTime, ap.ScheduledEndTime, ap.Status
    FROM Appointment ap INNER JOIN Patient p ON ap.PatientSerNum = p.PatientSerNum
        INNER JOIN Alias a ON a.AliasSerNum = ap.AliasSerNum
    WHERE p.PatientSerNum<35384
    UNION ALL 
    SELECT a.AliasName, p.PatientSerNum, p.PlanCreationDate, p.PlanCreationDate, p.Status
    FROM Plan p INNER JOIN Patient pa ON p.PatientSerNum = pa.PatientSerNum
        INNER JOIN Alias a ON a.AliasSerNum = p.AliasSerNum
    WHERE pa.PatientSerNum<35384
    UNION ALL
    SELECT DISTINCT a.AliasName, p.PatientSerNum, t.TreatmentDateTime, p.PlanCreationDate, p.Status 
    FROM TreatmentFieldHstry t INNER JOIN Plan p ON t.PlanSerNum = p.PlanSerNum
    INNER JOIN Alias a ON a.AliasSerNum = p.AliasSerNum
    INNER JOIN Patient pat ON pat.PatientSerNum = p.PatientSerNum
    WHERE pat.PatientSerNum<35384
    UNION ALL
    SELECT a.AliasName, d.PatientSerNum, d.ApprovedTimeStamp, d.DateOfService, d.ApprovalStatus
    FROM Document d INNER JOIN Patient p ON d.PatientSerNum = p.PatientSerNum
        INNER JOIN Alias a on d.AliasSerNum = a.AliasSerNum
    WHERE p.PatientSerNum<35384
    ORDER BY PatientSerNum, CreationDate
	""")

	#every line that can be iterated through with sequenceCursor now represents an event for a patient.

	full_set = []

	# IGNORE THESE COMMENTED OUT SEQUENCES

	# sequence = ['Ct-Sim', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR DOSE CALCULATION', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA' 'READY FOR TREATMENT'], 'READY FOR MD CONTOUR', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR MD CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], 'READY FOR DOSE CALCULATION', ['Ct-Sim', 'Consult', 'Consult Appointment','READY FOR DOSE CALCULATION', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], ['Prescription Document (Fast Track)','PRESCRIPTION APPROVED'], ['Ct-Sim', 'Consult', 'Consult Appointment','Prescription Document (Fast Track)','PRESCRIPTION APPROVED', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR DOSE CALCULATION', 'READY FOR TREATMENT'], 'READY FOR PHYSICS QA', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR PHYSICS QA', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)','READY FOR DOSE CALCULATION'], 'READY FOR TREATMENT']
	# not_array=[0, 5, 0, 5, 0, 5, 2, 5, 0, 5, 0]
	# status=[0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], [0,0],[0,0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0,0], 0]

	# sequence = ['Ct-Sim', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR DOSE CALCULATION', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA' 'READY FOR TREATMENT'], 'READY FOR MD CONTOUR', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR MD CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], 'READY FOR DOSE CALCULATION', ['Ct-Sim', 'Consult', 'Consult Appointment','READY FOR DOSE CALCULATION', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], ['Prescription Document (Fast Track)','PRESCRIPTION APPROVED'], ['Ct-Sim', 'Consult', 'Consult Appointment','Prescription Document (Fast Track)','PRESCRIPTION APPROVED', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR DOSE CALCULATION', 'READY FOR TREATMENT'], 'READY FOR PHYSICS QA', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR PHYSICS QA', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)','READY FOR DOSE CALCULATION'], 'READY FOR TREATMENT']
	# not_array=[0, 5, 0, 5, 0, 5, 2, 5, 0, 5, 0]
	# status=[0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], [0,0],[0,0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0,0], 0]

	# 

	# again, this is described in the oncotime report,
	# but briefly this means I want a sequence of events that looks like:
	# Ct-Sim followed by NOT (Ct-Sim or READY FOR DOSE....) followed by READY FOR MD CONTOUR followed
	# by NOT (a list of terms) etc.

	# ignore the status - this refers to whether the field in the database is flagged as active, closed, etc.

	sequence = ['Ct-Sim', ['Ct-Sim', 'READY FOR DOSE CALCULATION', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA' 'READY FOR TREATMENT'], 'READY FOR MD CONTOUR', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR MD CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], 'READY FOR DOSE CALCULATION', ['Ct-Sim', 'READY FOR DOSE CALCULATION', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], ['Prescription Document (Fast Track)','PRESCRIPTION APPROVED'], ['Ct-Sim', 'Prescription Document (Fast Track)','PRESCRIPTION APPROVED', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR DOSE CALCULATION', 'READY FOR TREATMENT'], 'READY FOR PHYSICS QA', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR PHYSICS QA', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)','READY FOR DOSE CALCULATION'], 'READY FOR TREATMENT']
	not_array=[0, 5, 0, 5, 0, 5, 2, 5, 0, 5, 0]
	status=[0, [0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0], [0,0],[0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0,0], 0]

	cancer_types = Set(['breast','prostate','lung','colon','thyroid', 'bone', 'ovary', 'tongue', 'Hodgkin\'s', 'leukaemia', 'liver', 'skin', 'brain', 'rectum', 'stomach', 'tonsil'])

	t = sequenceCursor.fetchone()
	serNum = t['PatientSerNum']
	curSerNum = serNum

	this_set = []

	# this while loop just iterates through the sequenceCursor, and creates the arr array for each patient (1 to 38000something)
	while (t is not None):
		arr = []
		while(curSerNum == serNum):
			# print t
			arr.append(t)
			t = sequenceCursor.fetchone()
			if t is None:
				break
			curSerNum = t['PatientSerNum']

		# Do the Sequence Extraction

		# this just copies the arrays that specify the matching sequence into new arrays
		# because the function findAll operates on the arrays by popping elements off the front of it
		new_sequence = sequence[:]
		new_not_array = not_array[:]
		new_status = status[:]

		# l is the array that the arrays of sequences get recursively added to
		l = []

		# findall is called passing in arr and the sequence specifiers
		a = findAll(arr, new_sequence, new_not_array, new_status, len(arr), l)

		# this is not strictly necessary, I just did this to remove duplicates from the set 
		# (converted to strings, made a hashset, copied them back into the a array)
		a_set = Set([])
		for elem in a:
			a_set.add(str(elem))

		a = []
		for elem in a_set:
			a.append(eval(elem))

		# this adds the actual row of data into this_set, corresponding to each valid patient timeseries that matches 
		# the sequence specifier
		# (remember findAll returns and array of arrays of indices of arr)

		for timeline in a:
			s = []
			for elem in timeline:
				s.append(arr[elem])

			this_set.append(s)

		if t is None:
			break
		# print "----"

		serNum = t['PatientSerNum']
		curSerNum = serNum
		# iterate on to the next patient, until the entire sequenceCursor is iterated through

	full_set = full_set + this_set

	# sequence = ['Ct-Sim', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR DOSE CALCULATION', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA' 'READY FOR TREATMENT'], 'READY FOR MD CONTOUR', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR MD CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], 'READY FOR DOSE CALCULATION', ['Ct-Sim', 'Consult', 'Consult Appointment','READY FOR DOSE CALCULATION', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], ['Prescription Document (Fast Track)','PRESCRIPTION APPROVED'], ['Ct-Sim', 'Consult', 'Consult Appointment','Prescription Document (Fast Track)','PRESCRIPTION APPROVED', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR DOSE CALCULATION', 'READY FOR TREATMENT'], 'READY FOR PHYSICS QA', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR PHYSICS QA', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)','READY FOR DOSE CALCULATION'], 'READY FOR TREATMENT']
	# not_array=[0, 5, 0, 5, 0, 5, 2, 5, 0, 5, 0]
	# status=[0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], [0,0],[0,0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0,0], 0]



	# this is just me experimenting with other sequences. The code is copy and pasted three times, violating
	# everything you and I ever learned about code reuse and programming. I am sorry. I remember I 
	# basically just spent a month trying to get the number to go down (the error in the prediction), 
	# and one way was by adding more training data (more valid sequences)

	sequence = ['READY FOR MD CONTOUR', '*', 'Ct-Sim', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR MD CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], 'READY FOR DOSE CALCULATION', ['Ct-Sim', 'Consult', 'Consult Appointment','READY FOR DOSE CALCULATION', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], ['Prescription Document (Fast Track)','PRESCRIPTION APPROVED'], ['Ct-Sim', 'Consult', 'Consult Appointment','Prescription Document (Fast Track)','PRESCRIPTION APPROVED', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR DOSE CALCULATION', 'READY FOR TREATMENT'], 'READY FOR PHYSICS QA', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR PHYSICS QA', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)','READY FOR DOSE CALCULATION'], 'READY FOR TREATMENT']
	not_array=[0, 6, 0, 5, 0, 5, 2, 5, 0, 5, 0]
	status=[0, 0, 0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], [0,0],[0,0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0,0], 0]

	# cancer_types = Set(['breast','prostate','lung','colon','thyroid', 'bone', 'ovary', 'tongue', 'Hodgkin\'s', 'leukaemia', 'liver', 'skin', 'brain', 'rectum', 'stomach', 'tonsil'])

	sequenceCursor.execute("""
    SELECT a.AliasName, t.PatientSerNum, t.CreationDate, t.CompletionDate, t.Status
    FROM Task t INNER JOIN Patient p ON p.PatientSerNum = t.PatientSerNum 
        INNER JOIN Alias a ON a.AliasSerNum = t.AliasSerNum 
    WHERE p.PatientSerNum<35384
    UNION ALL 
    SELECT a.AliasName, ap.PatientserNum, ap.ScheduledStartTime, ap.ScheduledEndTime, ap.Status
    FROM Appointment ap INNER JOIN Patient p ON ap.PatientSerNum = p.PatientSerNum
        INNER JOIN Alias a ON a.AliasSerNum = ap.AliasSerNum
    WHERE p.PatientSerNum<35384
    UNION ALL 
    SELECT a.AliasName, p.PatientSerNum, p.PlanCreationDate, p.PlanCreationDate, p.Status
    FROM Plan p INNER JOIN Patient pa ON p.PatientSerNum = pa.PatientSerNum
        INNER JOIN Alias a ON a.AliasSerNum = p.AliasSerNum
    WHERE pa.PatientSerNum<35384
    UNION ALL
    SELECT DISTINCT a.AliasName, p.PatientSerNum, t.TreatmentDateTime, p.PlanCreationDate, p.Status 
    FROM TreatmentFieldHstry t INNER JOIN Plan p ON t.PlanSerNum = p.PlanSerNum
    INNER JOIN Alias a ON a.AliasSerNum = p.AliasSerNum
    INNER JOIN Patient pat ON pat.PatientSerNum = p.PatientSerNum
    WHERE pat.PatientSerNum<35384
    UNION ALL
    SELECT a.AliasName, d.PatientSerNum, d.ApprovedTimeStamp, d.DateOfService, d.ApprovalStatus
    FROM Document d INNER JOIN Patient p ON d.PatientSerNum = p.PatientSerNum
        INNER JOIN Alias a on d.AliasSerNum = a.AliasSerNum
    WHERE p.PatientSerNum<35384
    ORDER BY PatientSerNum, CreationDate
	""")

	t = sequenceCursor.fetchone()
	serNum = t['PatientSerNum']
	curSerNum = serNum

	this_set = []

	while (t is not None):
		arr = []
		while(curSerNum == serNum):
			# print t
			arr.append(t)
			t = sequenceCursor.fetchone()
			if t is None:
				break
			curSerNum = t['PatientSerNum']

		# Do the Sequence Extraction
		new_sequence = sequence[:]
		new_not_array = not_array[:]
		new_status = status[:]


		l = []
		a = findAll(arr, new_sequence, new_not_array, new_status, len(arr), l)

		a_set = Set([])
		for elem in a:
			a_set.add(str(elem))

		a = []
		for elem in a_set:
			a.append(eval(elem))

		# print a
		for timeline in a:
			s = []
			for elem in timeline:
				s.append(arr[elem])

			this_set.append(s)

		if t is None:
			break
		# print "----"

		serNum = t['PatientSerNum']
		curSerNum = serNum

	full_set = full_set + this_set
	
	sequence = ['Ct-Sim', ['Ct-Sim', 'READY FOR DOSE CALCULATION', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA' 'READY FOR TREATMENT'], ['Prescription Document (Fast Track)','PRESCRIPTION APPROVED'], ['Ct-Sim', 'Prescription Document (Fast Track)','PRESCRIPTION APPROVED', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR DOSE CALCULATION', 'READY FOR TREATMENT'], 'READY FOR MD CONTOUR', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR MD CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'],  'READY FOR DOSE CALCULATION', ['Ct-Sim', 'READY FOR DOSE CALCULATION', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'READY FOR PHYSICS QA', 'READY FOR TREATMENT'], 'READY FOR PHYSICS QA', ['Ct-Sim', 'Consult', 'Consult Appointment', 'READY FOR PHYSICS QA', 'READY FOR MD CONTOUR', 'READY FOR CONTOUR', 'PRESCRIPTION APPROVED', 'Prescription Document (Fast Track)','READY FOR DOSE CALCULATION'], 'READY FOR TREATMENT']
	not_array=[0, 5, 2, 5, 0, 5,0, 5, 0, 5, 0]
	status=[0, [0,0,0,0,0,0], [0,0],[0,0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0], 0, [0,0,0,0,0,0], 0, [0,0,0,0,0,0,0,0,0], 0]	

	# cancer_types = Set(['breast','prostate','lung','colon','thyroid', 'bone', 'ovary', 'tongue', 'Hodgkin\'s', 'leukaemia', 'liver', 'skin', 'brain', 'rectum', 'stomach', 'tonsil'])

	sequenceCursor.execute("""
    SELECT a.AliasName, t.PatientSerNum, t.CreationDate, t.CompletionDate, t.Status
    FROM Task t INNER JOIN Patient p ON p.PatientSerNum = t.PatientSerNum 
        INNER JOIN Alias a ON a.AliasSerNum = t.AliasSerNum 
    WHERE p.PatientSerNum<35384
    UNION ALL 
    SELECT a.AliasName, ap.PatientserNum, ap.ScheduledStartTime, ap.ScheduledEndTime, ap.Status
    FROM Appointment ap INNER JOIN Patient p ON ap.PatientSerNum = p.PatientSerNum
        INNER JOIN Alias a ON a.AliasSerNum = ap.AliasSerNum
    WHERE p.PatientSerNum<35384
    UNION ALL 
    SELECT a.AliasName, p.PatientSerNum, p.PlanCreationDate, p.PlanCreationDate, p.Status
    FROM Plan p INNER JOIN Patient pa ON p.PatientSerNum = pa.PatientSerNum
        INNER JOIN Alias a ON a.AliasSerNum = p.AliasSerNum
    WHERE pa.PatientSerNum<35384
    UNION ALL
    SELECT DISTINCT a.AliasName, p.PatientSerNum, t.TreatmentDateTime, p.PlanCreationDate, p.Status 
    FROM TreatmentFieldHstry t INNER JOIN Plan p ON t.PlanSerNum = p.PlanSerNum
    INNER JOIN Alias a ON a.AliasSerNum = p.AliasSerNum
    INNER JOIN Patient pat ON pat.PatientSerNum = p.PatientSerNum
    WHERE pat.PatientSerNum<35384
    UNION ALL
    SELECT a.AliasName, d.PatientSerNum, d.ApprovedTimeStamp, d.DateOfService, d.ApprovalStatus
    FROM Document d INNER JOIN Patient p ON d.PatientSerNum = p.PatientSerNum
        INNER JOIN Alias a on d.AliasSerNum = a.AliasSerNum
    WHERE p.PatientSerNum<35384
    ORDER BY PatientSerNum, CreationDate
	""")

	t = sequenceCursor.fetchone()
	serNum = t['PatientSerNum']
	curSerNum = serNum

	this_set = []

	while (t is not None):
		arr = []
		while(curSerNum == serNum):
			# print t
			arr.append(t)
			t = sequenceCursor.fetchone()
			if t is None:
				break
			curSerNum = t['PatientSerNum']

		# Do the Sequence Extraction
		new_sequence = sequence[:]
		new_not_array = not_array[:]
		new_status = status[:]


		l = []
		a = findAll(arr, new_sequence, new_not_array, new_status, len(arr), l)

		a_set = Set([])
		for elem in a:
			a_set.add(str(elem))

		a = []
		for elem in a_set:
			a.append(eval(elem))

		# print a
		for timeline in a:
			s = []
			for elem in timeline:
				s.append(arr[elem])

			this_set.append(s)

		if t is None:
			break
		# print "----"

		serNum = t['PatientSerNum']
		curSerNum = serNum

	full_set = full_set + this_set


	# the following code simply creates a bunch of dictionaries so that for each timeline that I add
	# to the training data, I can add the features (the patient's doctor, priority, diagnosis)


	# write timelines to multimap: patient -> list(timelines)
	patient_to_timeseries = defaultdict(list)

	for line in full_set:
		timeline = []
		for item in line:
			timeline.append(item['CreationDate'])

		patient_to_timeseries[line[0]['PatientSerNum']].append(timeline)

	diagnosisCursor = mysql_cn.cursor(MySQLdb.cursors.DictCursor)

	# extracts all diagnoses from the database, does some processing before mapping a patient to 
	# a diagnosis (splitting up the term, making sure it is only in the list of cancers specified in 
	# cancer_types)
	diagnosisCursor.execute(""" 
	SELECT diag.PatientSerNum, diag.DiagnosisCreationDate, diag.DiagnosisCode, diag.Description
	FROM Patient p INNER JOIN Diagnosis diag ON p.PatientSerNum = diag.PatientSerNum
	ORDER BY PatientSerNum;
	""")

	patient_to_all_diagnoses = defaultdict(list)

	for row in diagnosisCursor:
		splitDesc = re.split(',| ', row['Description'])
		fields = Set(splitDesc)

		for cancer in cancer_types:
			if cancer in fields:
				patient_to_all_diagnoses[row['PatientSerNum']].append(cancer)

	## test patients_to_all_diagnoses

	# for k, v in patient_to_all_diagnoses.items():
	# 	print k
	# 	print "::"
	# 	for w in v:
	# 		print w

	# 	print "====="

	# get patient_to_oncologist

	doctorCursor = mysql_cn.cursor(MySQLdb.cursors.DictCursor)
	
	# straightforward - maps patient to their PRIMARY oncologist (the one wiht oncologist flag
	# in the database set to 1)
	doctorCursor.execute("""
	SELECT pd.PatientSerNum, pd.DoctorSerNum, pd.OncologistFlag, pd.PrimaryFlag
	FROM PatientDoctor pd INNER JOIN Doctor d ON d.DoctorSerNum = pd.DoctorSerNum
	ORDER BY pd.PatientSerNum;
	""")

	patient_to_oncologist = dict()
	patient_to_all_oncologists = defaultdict(list)
	all_oncologists = Set([])

	for row in doctorCursor:
		if row['OncologistFlag']==1:
			patient_to_all_oncologists[row['PatientSerNum']].append(row['DoctorSerNum'])
			all_oncologists.add(row['DoctorSerNum'])
		# if row['OncologistFlag']==1 and row['PrimaryFlag']==1:
		# 	patient_to_oncologist[row['PatientSerNum']]=row['DoctorSerNum']
		# 	all_oncologists.add(row['DoctorSerNum'])

	# print all_oncologists

	# get patient_to_years

	patientCursor = mysql_cn.cursor(MySQLdb.cursors.DictCursor)

	# extracts and maps patients to their age in years - I ended up taking this feature out because
	# it actually made the prediction worse. Maybe you can play with this as well though...

	patientCursor.execute("""
		SELECT * FROM Patient ORDER BY PatientSerNum;
	""")

	patient_to_years = dict()
	for row in patientCursor:
		if (int(row['DateOfBirth'])!=1970): # remove 1970????
			patient_to_years[row['PatientSerNum']]=(2015-int(row['DateOfBirth']))

	## test patient_to_years

	# for k,v in patient_to_years.items():
	# 	print str(k) + "::" + str(v)

	# valid = 0
	# for k, v in patient_to_timeseries.items():
	# 	if k in patient_to_years.keys():
	# 		valid += 1

	# print valid

	# get patient_to_priority

	priorityCursor = mysql_cn.cursor(MySQLdb.cursors.DictCursor)

	# extracts and maps the patient to the treatment priority - P1 is highest priority and therefore
	# is usually completed fastest, P4 is the slowest, etc. Usually this is available as a feature because
	# the priority is set at the start of treatment, but not always, and the priority can change halfway through
	# , etc... it's complicated

	priorityCursor.execute("""
		SELECT * FROM Priority;
	""")

	priorities_list = ['SGAS_P1', 'SGAS_P2', 'SGAS_P3', 'SGAS_P4']
	all_priorities = Set([])
	patient_to_priority = dict()

	patient_to_priority_counts = dict()
	# find max number of counts of priority level
	for row in priorityCursor:
		if row['PatientSerNum'] not in patient_to_priority_counts.keys():
			patient_to_priority_counts[row['PatientSerNum']] = [0,0,0,0]
			for i in range(len(priorities_list)):
				if priorities_list[i]==row['PriorityCode']:
					patient_to_priority_counts[row['PatientSerNum']][i] += 1
					break
		else:
			for i in range(len(priorities_list)):
				if priorities_list[i]==row['PriorityCode']:
					patient_to_priority_counts[row['PatientSerNum']][i] += 1
					break

	for k, v in patient_to_priority_counts.items():
		index = 0
		cur_max = 0
		for i in range(len(v)):
			if v[i] > cur_max:
				cur_max = v[i]
				index = i

		patient_to_priority[k] = priorities_list[index]

	# for k, v in patient_to_priority.items():
	# 	print str(k) + " --> " + str(v)


	print "Done Populating Dictionaries"
	# Predictor


	# X_matrix is the matrix of all of the training (and testing) data.

	X_matrix = []
	target_set = []
	target_starts = []
	target_ends = []

	# make oncologist, cancer_type lists
	onc_list = []
	cancer_types_list = []

	for t in all_oncologists:
		onc_list.append(t)

	# print onc_list

	for t in cancer_types:
		cancer_types_list.append(t)

	qc_holidays = Holidays(country='CA', prov='QC')


	print "Done Writing TSVs"

	# do timelines first patient course or not


	# this appends a flag (1 or 0) that indicates whether or not
	# this was the first treatment course the patient went through (whether
	# it was the first valid sequence extracted using the sequence extractor) - for later use when I add
	# features to X_matrix
	for k, v in patient_to_timeseries.items():
		ct_sim_times = []
		for w in v:
			ct_sim_times.append(w[0])

		min_ct_sim_time = min(ct_sim_times)
		for w in v:
			if w[0] == min_ct_sim_time:
				w.append(1.0)
			else:
				w.append(0.0)



	print "Done First or Not"

	# create X_matrix and target_set
	# the features include:
	# - all the diagnoses, 1 if the patient has that diagnosis, 0 if not (more than one diagnosis may have a 1)
	# - all the oncologists, 1 if the patient is overseen by that oncologist (not only the primary oncologist - I think this made the predictor better)
	# - all the priorities, 1 or 0
	# - whether it was the first treatment course of the patient

	for k, v in patient_to_timeseries.items():
		first = True
		for w in v:
			new_feature_vector = []

			if k in patient_to_all_diagnoses.keys():
				for cancer in cancer_types_list:
					if cancer in patient_to_all_diagnoses[k]:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				break

			if k in patient_to_all_oncologists.keys():
				for oncologist in onc_list:
					if oncologist in patient_to_all_oncologists[k]:
					# if patient_to_oncologist[k]==oncologist:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				break

			# if k in patient_to_years.keys():
			# 	new_feature_vector.append(float(patient_to_years[k]))
			# else:
			# 	break

			if k in patient_to_priority.keys():
				for priority in priorities_list:
					if patient_to_priority[k]==priority:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				break

			if w[6] == float(1.0):
				new_feature_vector.append(float(0.0))
				# print "1.0"
			else:
				new_feature_vector.append(float(1.0))
				# print "0.0"

			# new_feature_vector.append(float(w[7]))

			# if first==True:
			# 	new_feature_vector.append(float(1.0))
			# else:
			# 	new_feature_vector.append(float(0.0))


			# the y value (the regression value, the target, etc) is the 6th time in the timeseries 
			# minus the 1st time (w[5] - w[0]) - the time between Ct-Sim and Ready for Treatment.

			# it was important to take away the weekends and holidays in the final timedelta of days
			# this improved the prediction error from 3 days to about 1.5 days.

			if (w[5]-w[0]).days < 35: #only take one from each patient???
				X_matrix.append(new_feature_vector)
				# remove weekends
				total_time = (w[5]-w[0]).total_seconds()/float(60*60*24)
				# print "Before: " + str(total_time)
				t_0 = w[0]
				t_5 = w[5]
				to_subtract = 0
				while (t_0 < t_5):
					if (t_0.weekday()==5 or t_0.weekday()==6 or (t_0.date() in qc_holidays)):
						to_subtract += 1
					t_0 += timedelta(days=1)

				total_time = total_time - float(to_subtract)
				if (total_time < 0):
					total_time = 0.0

				# print "After: " + str(total_time)

				target_set.append(total_time)

			first = False

	print "Done Building Matrix"
	# just separating the X_matrix into training and testing sets

	training_set = [X_matrix[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	testing_set = [X_matrix[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	target_1 = [target_set[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	target_2 = [target_set[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]
	# for i in range(0,20):
	# 	print str(X_matrix[i]) + " -> " + str(target_set[i])



	print "Number of training samples: " + str(len(X_matrix))
	print "Number of target values: " + str(len(target_set))

	# machine learning (ridge regression algorithm - I think this is the same thing as L2 regularization?) - 
	# anyways I just used the library... tried playing with parameters and stuff too for a long time

	clf = linear_model.RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 20.0, 30.0, 50.0, 100.0, 1000.0])
	clf.fit(X_matrix, target_set)


	# just pickling the predictor 
	pickle.dump(clf, open( "regularized_linear_regression_clf_initial.p", "wb" ))



	# Here, I was trying to add features that correspond to given we are already in the middle of treatment,
	# aka we already did Ct-sim and MD contour, for example, we can add those real waiting times 
	# into the prediction model. This ended up not really improving anything, because the majority
	# of the waiting time was split between two stages only - MD contour and dosimetry.

	print "Making a map of all patients to Ct-Sims"

	sequenceCursor.execute("""
		SELECT ap.PatientserNum, a.AliasName, ap.ScheduledStartTime FROM Appointment ap 
			INNER JOIN Alias a ON a.AliasSerNum=ap.AliasSerNum 
		WHERE a.AliasName='Ct-Sim' ORDER BY ap.PatientSerNum
	""")

	t = sequenceCursor.fetchone()
	patient_to_ctstarttimes = defaultdict(list)

	while (t is not None):
		this_pat = t['PatientserNum']
		this_time = t['ScheduledStartTime']

		to_append = []
		to_append.append(this_time)
		patient_to_ctstarttimes[this_pat].append(to_append)
		t = sequenceCursor.fetchone()


	print "Making Predictions for all Ct-Sims"

	for k, v in patient_to_ctstarttimes.items():
		for w in v:
			new_feature_vector = []

			if k in patient_to_all_diagnoses.keys():
				for cancer in cancer_types_list:
					if cancer in patient_to_all_diagnoses[k]:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				w.append(0)
				w.append(0)
				break
			
			if k in patient_to_all_oncologists.keys():
				for oncologist in onc_list:
					if oncologist in patient_to_all_oncologists[k]:
					# if patient_to_oncologist[k]==oncologist:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				w.append(0)
				w.append(0)
				break

			if k in patient_to_priority.keys():
				for priority in priorities_list:
					if patient_to_priority[k]==priority:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				w.append(0)
				w.append(0)
				break

			ct_sim_times = []
			for sub in v:
				ct_sim_times.append(sub[0])

			min_ct_sim_time = min(ct_sim_times)
			if w == min_ct_sim_time:
				new_feature_vector.append(1.0)
			else:
				new_feature_vector.append(0.0)

			w.append(1)
			prediction = clf.predict(new_feature_vector)
			# predicted_end_date = addWithWeekends(w[0], prediction, qc_holidays)
			predicted_end_date = w[0] + timedelta(days=prediction)
			w.append(predicted_end_date)

		# for w in v:
		# 	print len(w)



	# there are 5 x_matrices because, as expected, there are five possible stages in between that
	# we can add extra waiting time information in.
	print "Finally Adding Business Parameter/Stages:"
	X_matrix = []
	target_set = []

	X_matrix_1 = []
	X_matrix_2 = []
	X_matrix_3 = []
	X_matrix_4 = []
	X_matrix_5 = []

	target_set_1 = []
	target_set_2 = []
	target_set_3 = []
	target_set_4 = []
	target_set_5 = []

	for k, v in patient_to_timeseries.items():
		first = True
		for w in v:
			new_feature_vector = []

			if k in patient_to_all_diagnoses.keys():
				for cancer in cancer_types_list:
					if cancer in patient_to_all_diagnoses[k]:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				break

			if k in patient_to_all_oncologists.keys():
				for oncologist in onc_list:
					if oncologist in patient_to_all_oncologists[k]:
					# if patient_to_oncologist[k]==oncologist:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				break

			# if k in patient_to_years.keys():
			# 	new_feature_vector.append(float(patient_to_years[k]))
			# else:
			# 	break

			if k in patient_to_priority.keys():
				for priority in priorities_list:
					if patient_to_priority[k]==priority:
						new_feature_vector.append(float(1.0))
					else:
						new_feature_vector.append(float(0.0))
			else:
				break

			if w[6] == float(1.0):
				new_feature_vector.append(float(0.0))
				# print "1.0"
			else:
				new_feature_vector.append(float(1.0))
				# print "0.0"

			# new_feature_vector.append(float(w[7]))

			# if first==True:
			# 	new_feature_vector.append(float(1.0))
			# else:
			# 	new_feature_vector.append(float(0.0))

			if (w[5]-w[0]).days < 35: #only take one from each patient???
				others = 0
				real_timedelta = w[5] - w[0]
				half_timedelta = real_timedelta/4 #can you do this?
				half_time = w[0] + 4*half_timedelta

				for a, b in patient_to_ctstarttimes.items():
					for c in b:
						if len(c)>1:
							if c[1] == 1:
								if (c[0] < w[0] and c[2] > w[0]) or (c[0] > w[0] and c[0] < half_time):
									others += 1

				# print others
				w.append(others)
				new_feature_vector.append(others)
				X_matrix.append(new_feature_vector)

				# Ct-Sim Segment Included
				new_feature_vector = new_feature_vector[:]
				new_feature_vector.append((w[1]-w[0]).days)
				X_matrix_1.append(new_feature_vector)

				# MD Contour Segment Included
				new_feature_vector = new_feature_vector[:]
				new_feature_vector.append((w[2]-w[1]).days)
				X_matrix_2.append(new_feature_vector)

				# Dosimetry Segment Included
				new_feature_vector = new_feature_vector[:]
				new_feature_vector.append((w[3]-w[2]).days)
				X_matrix_3.append(new_feature_vector)

				# Prescription Approved Segment Included
				new_feature_vector = new_feature_vector[:]
				new_feature_vector.append((w[4]-w[3]).days)
				X_matrix_4.append(new_feature_vector)

				# Ready for Physics QA Segment Included
				new_feature_vector = new_feature_vector[:]
				new_feature_vector.append((w[5]-w[4]).days)
				X_matrix_5.append(new_feature_vector)

				target_set.append(actualTime(w, 5, 0, qc_holidays))
				target_set_1.append(actualTime(w, 5, 1, qc_holidays))
				target_set_2.append(actualTime(w, 5, 2, qc_holidays))
				target_set_3.append(actualTime(w, 5, 3, qc_holidays))
				target_set_4.append(actualTime(w, 5, 4, qc_holidays))
				# target_set_5.append(actualTime(w, 5, 5, qc_holidays))

			first = False


	# i also pickled all the dictionaries into files because creating them
	# takes a non-negligable amount of time.
	pickle.dump(patient_to_ctstarttimes, open("patient_to_ctstarttimes.p", "wb"))
	pickle.dump(patient_to_timeseries, open("patient_to_timeseries.p", "wb"))
	pickle.dump(patient_to_priority, open("patient_to_priority.p", "wb"))
	pickle.dump(patient_to_all_diagnoses, open("patient_to_all_diagnoses.p", "wb"))
	pickle.dump(patient_to_all_oncologists, open("patient_to_all_oncologists.p", "wb"))
	pickle.dump(cancer_types_list, open("cancer_types_list.p", "wb"))
	pickle.dump(onc_list, open("onc_list.p", "wb"))
	pickle.dump(priorities_list, open("priorities_list.p", "wb"))

	# Train all the X_Matrices, pickle them

	training_set = [X_matrix[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	testing_set = [X_matrix[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	target_1 = [target_set[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	target_2 = [target_set[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	clf = linear_model.RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 20.0, 30.0, 50.0, 100.0, 1000.0])
	clf.fit(training_set, target_1)

	# clf.predict and poof - we get an array of predictions for the testing set!
	preds = clf.predict(testing_set)

	error_set = []
	for i in range(0, len(preds)):
		error = abs(preds[i] - target_2[i])
		error_set.append(error)

	# just calculated the average absolute value error - other errors may be more appropriate (squared?)
	print "Average Absolute Value Error for Regularized Linear Regression: " + str(numpy.mean(error_set))
	print "Stdev of Error: " + str(numpy.std(error_set))

	pickle.dump(clf, open( "regularized_linear_regression_clf.p", "wb" ))

	print "Done Pickling X_matrix"




	X_matrix = X_matrix_1
	target_set = target_set_1

	training_set = [X_matrix[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	testing_set = [X_matrix[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	target_1 = [target_set[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	target_2 = [target_set[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	clf = linear_model.RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 20.0, 30.0, 50.0, 100.0, 1000.0])
	clf.fit(training_set, target_1)

	preds = clf.predict(testing_set)

	error_set = []
	for i in range(0, len(preds)):
		error = abs(preds[i] - target_2[i])
		error_set.append(error)

	print "Average Absolute Value Error for Regularized Linear Regression: " + str(numpy.mean(error_set))
	print "Stdev of Error: " + str(numpy.std(error_set))

	pickle.dump(clf, open( "regularized_linear_regression_clf_1.p", "wb" ))

	# Here i'm just pickling the rest of the trained models for each x_matrix
	print "Done Pickling X_matrix_1"




	X_matrix = X_matrix_2
	target_set = target_set_2

	training_set = [X_matrix[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	testing_set = [X_matrix[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	target_1 = [target_set[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	target_2 = [target_set[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	clf = linear_model.RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 20.0, 30.0, 50.0, 100.0, 1000.0])
	clf.fit(training_set, target_1)

	preds = clf.predict(testing_set)

	error_set = []
	for i in range(0, len(preds)):
		error = abs(preds[i] - target_2[i])
		error_set.append(error)

	print "Average Absolute Value Error for Regularized Linear Regression: " + str(numpy.mean(error_set))
	print "Stdev of Error: " + str(numpy.std(error_set))

	pickle.dump(clf, open( "regularized_linear_regression_clf_2.p", "wb" ))

	print "Done Pickling X_matrix_2"


	X_matrix = X_matrix_3
	target_set = target_set_3

	training_set = [X_matrix[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	testing_set = [X_matrix[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	target_1 = [target_set[i] for i in range(0, len(X_matrix) - len(X_matrix)/5)]
	target_2 = [target_set[i] for i in range(len(X_matrix)-len(X_matrix)/5, len(X_matrix))]

	clf = linear_model.RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 20.0, 30.0, 50.0, 100.0, 1000.0])
	clf.fit(training_set, target_1)

	preds = clf.predict(testing_set)

	error_set = []
	for i in range(0, len(preds)):
		error = abs(preds[i] - target_2[i])
		error_set.append(error)

	print "Average Absolute Value Error for Regularized Linear Regression: " + str(numpy.mean(error_set))
	print "Stdev of Error: " + str(numpy.std(error_set))

	pickle.dump(clf, open( "regularized_linear_regression_clf_3.p", "wb" ))

	print "Done Pickling X_matrix_3"


	# svr_days = []
	# actual_days = []
	# labels = []

	# for i in range(50):
	# 	# svr_days.append(y_lin[i+50])
	# 	# actual_days.append(target_2[i+50])
	# 	svr_days.append(preds[i+50])
	# 	actual_days.append(target_2[i+50])		
	# 	labels.append(str(i))

	# # print "here"
	# N = 50
	# ind = numpy.arange(N)
	# width = 0.35

	# fig, ax = plt.subplots()

	# rects0 = ax.bar(ind, svr_days, width, color='r')
	# rects1 = ax.bar(ind+width, actual_days, width, color='g')

	# x = range(50)
	# y = []
	# for i in x:
	# 	y.append(14)

	# ax.plot(x,y)

	# ax.set_ylabel('Days')
	# ax.set_title('A comparison of our estimate and the actual wait time for the first 50 test cases')
	# ax.set_xticks(ind + width)
	# ax.set_xticklabels(labels)
	# plt.yticks(numpy.arange(0, 22, 1))
	# plt.ylim(ymin=0, ymax=22)

	# plt.ylim(ymin=0)

	# plt.show()

	# svm

	# svr_lin = svm.SVR(kernel='linear', C=1e3)
	# # svr_poly = svm.SVR(kernel='poly', C=1e3, degree=2)

	# svr_pred = svr_lin.fit(training_set, target_1)
	# y_lin = svr_pred.predict(testing_set)
	# # y_lin = svr_lin.fit(training_set, target_1).predict(testing_set)
	# # y_poly = svr_poly.fit(training_set, target_1).predict(testing_set)

	# error_lin = []
	# # error_poly = []

	# for i in range(0, len(y_lin)):
	# 	error2 = abs(y_lin[i] - target_2[i])
	# 	# error3 = abs(y_poly[i] - target_2[i])

	# 	error_lin.append(error2)
	# 	# error_poly.append(error3)

	# print "Average Absolute Value Error, linear SVM: " + str(numpy.mean(error_lin))
	# print "Stdev of Error, linear SVM: " + str(numpy.std(error_lin))

	# pickle.dump(svr_pred, open( "svr_pred.p", "wb" ))



if __name__ == "__main__":
	main()