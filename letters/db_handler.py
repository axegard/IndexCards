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