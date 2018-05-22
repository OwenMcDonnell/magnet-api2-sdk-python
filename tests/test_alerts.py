import json
from datetime import datetime
from magnetsdk2.connection import Connection
from magnetsdk2.connection_test import ConnectionTest
from magnetsdk2.iterator import FilePersistentAlertIterator
import ipdb

conn2 = Connection()
conn = ConnectionTest()
org_id = '149ab4da-ab74-11e6-9671-0a7e67dda05f'
organization_id = org_id

def test_connection_org():
	conn = ConnectionTest()
	org_id = '149ab4da-ab74-11e6-9671-0a7e67dda05f'

	## testing ConnectionTest.get_me
	assert json.loads(conn.get_me())['email'] == u'demo@niddel.com'

	## testing ConnectionTest.iter_organizations
	assert json.loads(conn.iter_organizations())['id'] == u'149ab4da-ab74-11e6-9671-0a7e67dda05f'
	assert json.loads(conn.iter_organizations())['name'] == u"Demo Organization"
	assert json.loads(conn.iter_organizations())['nickname'] == u"NiddelDemo"
	assert json.loads(conn.iter_organizations())['properties']['bucket'] == u'niddel-149ab4da-ab74-11e6-9671-0a7e67dda05f'
	assert json.loads(conn.iter_organizations())['properties']['bucketRegion'] == u'us-east-1'
	assert json.loads(conn.iter_organizations())['properties']['bucketReportPrefix'] == u'reports'
	assert json.loads(conn.iter_organizations())['properties']['bucketUploadPrefix'] == u'upload'
	assert json.loads(conn.iter_organizations())['properties']['maxBlacklists'] == 500
	assert json.loads(conn.iter_organizations())['properties']['maxWhitelists'] == 500
	assert json.loads(conn.iter_organizations())['roles'] == [u'admin']
	assert json.loads(conn.iter_organizations())['status'] == "suspended"
	## testing ConnectionTest.get_organization
	assert json.loads(conn.get_organization(org_id))['id'] == u'149ab4da-ab74-11e6-9671-0a7e67dda05f'
	assert json.loads(conn.get_organization(org_id))['name'] == u"Demo Organization"
	assert json.loads(conn.get_organization(org_id))['nickname'] == u"NiddelDemo"
	assert json.loads(conn.get_organization(org_id))['properties']['bucket'] == u'niddel-149ab4da-ab74-11e6-9671-0a7e67dda05f'
	assert json.loads(conn.get_organization(org_id))['properties']['bucketRegion'] == u'us-east-1'
	assert json.loads(conn.get_organization(org_id))['properties']['bucketReportPrefix'] == u'reports'
	assert json.loads(conn.get_organization(org_id))['properties']['bucketUploadPrefix'] == u'upload'
	assert json.loads(conn.get_organization(org_id))['properties']['maxBlacklists'] == 500
	assert json.loads(conn.get_organization(org_id))['properties']['maxWhitelists'] == 500
	assert json.loads(conn.get_organization(org_id))['roles'] == [u'admin']
	assert json.loads(conn.get_organization(org_id))['status'] == "suspended"

def test_connection_alerts():
	conn = ConnectionTest()
	org_id = '149ab4da-ab74-11e6-9671-0a7e67dda05f'
	created_at = '2018-05-10T00:00:00Z' #str(datetime.now().strftime("%Y-%m-%d") + 'T00:00:00Z')

	for alert in conn.iter_organization_alerts_timeline(organization_id = org_id, createdAt = created_at):
		if alert:
			assert alert['createdAt'] > created_at

def test_connection_alerts_persistence():
	org_id = '349ab4da-ab74-11e6-9671-0a7e67dda05f'
	conn = ConnectionTest()
	alert_iterator = FilePersistentAlertIterator('persistence.json', conn, org_id)

	for alert in alert_iterator:
		if alert:
			try:
				#ipdb.set_trace()
				assert is_valid_alert_createdAt(alert['createdAt'])
			except:
				alert_iterator.load()
			else:
				alert_iterator.save()
