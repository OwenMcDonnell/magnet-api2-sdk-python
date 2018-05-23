import json
from datetime import datetime
#from magnetsdk2.connection import Connection
from tests.connection_test import ConnectionTest
from magnetsdk2.iterator import FilePersistentAlertIterator
from magnetsdk2.validation import is_valid_uuid

#conn2 = Connection()
conn = ConnectionTest()

def test_connection_org():
	org_id = conn.iter_organizations()[0]

	## testing ConnectionTest.get_me
	assert json.loads(conn.get_me())['email'] == u'demo@niddel.com'

	## testing ConnectionTest.iter_organizations
	for org in conn.iter_organizations():
		assert is_valid_uuid(org)
	
	## testing ConnectionTest.get_organization
	assert is_valid_uuid(json.loads(conn.get_organization(org_id))['id'])
	assert json.loads(conn.get_organization(org_id))['id'] == org_id
	assert json.loads(conn.get_organization(org_id))['name'] == u"Demo Organization"
	assert json.loads(conn.get_organization(org_id))['nickname'] == u"NiddelDemo"
	assert json.loads(conn.get_organization(org_id))['properties']['bucket'] == u'niddel-' + org_id
	assert json.loads(conn.get_organization(org_id))['properties']['bucketRegion'] == u'us-east-1'
	assert json.loads(conn.get_organization(org_id))['properties']['bucketReportPrefix'] == u'reports'
	assert json.loads(conn.get_organization(org_id))['properties']['bucketUploadPrefix'] == u'upload'
	assert json.loads(conn.get_organization(org_id))['properties']['maxBlacklists'] == 500
	assert json.loads(conn.get_organization(org_id))['properties']['maxWhitelists'] == 500
	assert json.loads(conn.get_organization(org_id))['roles'] == [u'admin']
	assert json.loads(conn.get_organization(org_id))['status'] == "suspended"

def test_connection_alerts():
	for org_id in conn.iter_organizations():
		for alert in conn.iter_organization_alerts_timeline(organization_id = org_id):
			assert is_valid_uuid(alert['id'])

def test_connection_alerts_persistence():
	for org_id in conn.iter_organizations():
		alert_iterator = FilePersistentAlertIterator(str(org_id + '_persistence.json'), conn, organization_id = org_id)
		for alert in alert_iterator:
			if alert:
				try:
					print org_id
					print alert
					#assert is_valid_uuid(alert['id'])
				except:
					alert_iterator.load()
				else:
					alert_iterator.save()
