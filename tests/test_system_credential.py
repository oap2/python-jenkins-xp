import json
from mock import patch

import jenkins
from tests.base import JenkinsTestBase


class JenkinsCredentialTestBase(JenkinsTestBase):
    config_xml = """<com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
        <scope>GLOBAL</scope>
        <id>Test System Credential</id>
        <username>Test-Admin</username>
        <password>secret123</password>
      </com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>"""


class JenkinsGetTagTextTest(JenkinsCredentialTestBase):

    def test_simple(self):
        name_to_return = self.j._get_tag_text('id', self.config_xml)
        self.assertEqual('Test System Credential', name_to_return)

    def test_failed(self):
        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j._get_tag_text('id', '<xml></xml>')
        self.assertEqual(str(context_manager.exception),
                         'tag[id] is invalidated')

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j._get_tag_text('id', '<xml><id></id></xml>')
        self.assertEqual(str(context_manager.exception),
                         'tag[id] is invalidated')

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j._get_tag_text('id', '<xml><id>   </id></xml>')
        self.assertEqual(str(context_manager.exception),
                         'tag[id] is invalidated')


class JenkinsAssertCredentialTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_system_credential_missing(self, jenkins_mock):
        jenkins_mock.side_effect = [
            jenkins.NotFoundException()
        ]

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j.assert_system_credential_exists('NonExistent')
        self.assertEqual(
            str(context_manager.exception),
            'credential[NonExistent] does not exist'
            ' in the domain[_] of Jenkins System')
        self._check_requests(jenkins_mock.call_args_list)

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_system_credential_exists(self, jenkins_mock):
        jenkins_mock.side_effect = [
            json.dumps({'id': 'ExistingCredential'})
        ]
        self.j.assert_system_credential_exists('ExistingCredential')
        self._check_requests(jenkins_mock.call_args_list)


class JenkinsCredentialExistsTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_system_credential_missing(self, jenkins_mock):
        jenkins_mock.side_effect = [
            jenkins.NotFoundException()
        ]

        self.assertEqual(self.j.system_credential_exists('NonExistent'),
                         False)
        self._check_requests(jenkins_mock.call_args_list)

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_system_credential_exists(self, jenkins_mock):
        jenkins_mock.side_effect = [
            json.dumps({'id': 'ExistingCredential'})
        ]

        self.assertEqual(self.j.system_credential_exists('ExistingCredential'),
                         True)
        self._check_requests(jenkins_mock.call_args_list)


class JenkinsGetCredentialInfoTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_simple(self, jenkins_mock):
        credential_info_to_return = {'id': 'ExistingCredential'}
        jenkins_mock.side_effect = [
            json.dumps(credential_info_to_return)
        ]

        credential_info = self.j.get_system_credential_info('ExistingCredential')

        self.assertEqual(credential_info, credential_info_to_return)
        self.assertEqual(
            jenkins_mock.call_args[0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/credential/ExistingCredential/api/json?depth=0'))
        self._check_requests(jenkins_mock.call_args_list)

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_nonexistent(self, jenkins_mock):
        jenkins_mock.side_effect = [
            None,
        ]

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j.get_system_credential_info('NonExistent')

        self.assertEqual(
            str(context_manager.exception),
            'credential[NonExistent] does not exist '
            'in the domain[_] of Jenkins System')

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_invalid_json(self, jenkins_mock):
        jenkins_mock.side_effect = [
            '{invalid_json}'
        ]

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j.get_system_credential_info('NonExistent')

        self.assertEqual(
            str(context_manager.exception),
            'Could not parse JSON info for credential[NonExistent]'
            ' in the domain[_] of Jenkins System')


class JenkinsGetCredentialConfigTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_encodes_credential_name(self, jenkins_mock):
        jenkins_mock.side_effect = [
            None,
        ]
        self.j.get_system_credential_config(u'Test System Credential')

        self.assertEqual(
            jenkins_mock.call_args_list[0][0][0].url,
            self.make_url('credentials/store/system/domain/'
                          '_/credential/Test%20System%20Credential/config.xml'))
        self._check_requests(jenkins_mock.call_args_list)


class JenkinsCreateCredentialTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_simple(self, jenkins_mock):
        jenkins_mock.side_effect = [
            jenkins.NotFoundException(),
            None,
            json.dumps({'id': 'Test System Credential'}),
            json.dumps({'_class': 'com.cloudbees.plugins.credentials.CredentialsStoreAction$DomainWrapper'}),
            json.dumps({'id': 'Test System Credential'}),
        ]

        self.j.create_system_credential(self.config_xml)
        self.assertEqual(
            jenkins_mock.call_args_list[1][0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/createCredentials'))

        self.assertEqual(
            jenkins_mock.call_args_list[2][0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/credential/Test%20System%20Credential/api/json?depth=0'))
        self._check_requests(jenkins_mock.call_args_list)

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_already_exists(self, jenkins_mock):
        jenkins_mock.side_effect = [
            json.dumps({'id': 'Test System Credential'}),
        ]

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j.create_system_credential(self.config_xml)
        self.assertEqual(
            jenkins_mock.call_args_list[0][0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/credential/Test%20System%20Credential/api/json?depth=0'))

        self.assertEqual(
            str(context_manager.exception),
            'credential[Test System Credential] already exists'
            ' in the domain[_] of Jenkins System')
        self._check_requests(jenkins_mock.call_args_list)

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_failed(self, jenkins_mock):
        jenkins_mock.side_effect = [
            jenkins.NotFoundException(),
            None,
            jenkins.NotFoundException(),
            json.dumps({'_class': 'com.cloudbees.plugins.credentials.CredentialsStoreAction$DomainWrapper'}),
            None,
        ]

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j.create_system_credential(self.config_xml)
        self.assertEqual(
            jenkins_mock.call_args_list[2][0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/credential/Test%20System%20Credential/api/json?depth=0'))
        self.assertEqual(
            jenkins_mock.call_args_list[1][0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/createCredentials'))
        self.assertEqual(
            str(context_manager.exception),
            'create[Test System Credential] failed in the domain[_] of Jenkins System')
        self._check_requests(jenkins_mock.call_args_list)


class JenkinsDeleteCredentialTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_simple(self, jenkins_mock):
        jenkins_mock.side_effect = [
            True,
            jenkins.NotFoundException(),
        ]

        self.j.delete_system_credential(u'Test Credential')

        self.assertEqual(
            jenkins_mock.call_args_list[0][0][0].url,
            self.make_url('credentials/store/system/domain/'
                          '_/credential/Test%20Credential/config.xml'))
        self._check_requests(jenkins_mock.call_args_list)

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_failed(self, jenkins_mock):
        jenkins_mock.side_effect = [
            json.dumps({'id': 'ExistingCredential'}),
            json.dumps({'id': 'ExistingCredential'}),
            json.dumps({'id': 'ExistingCredential'})
        ]

        with self.assertRaises(jenkins.JenkinsException) as context_manager:
            self.j.delete_system_credential(u'ExistingCredential')
        self.assertEqual(
            jenkins_mock.call_args_list[0][0][0].url,
            self.make_url('credentials/store/system/'
                          'domain/_/credential/ExistingCredential/config.xml'))
        self.assertEqual(
            str(context_manager.exception),
            'delete credential[ExistingCredential] from '
            'domain[_] of Jenkins System failed')
        self._check_requests(jenkins_mock.call_args_list)


class JenkinsReconfigCredentialTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_simple(self, jenkins_mock):
        jenkins_mock.side_effect = [
            json.dumps({'id': 'Test System Credential'}),
            None
        ]

        self.j.reconfig_system_credential(self.config_xml)

        self.assertEqual(
            jenkins_mock.call_args_list[1][0][0].url,
            self.make_url('credentials/store/system/domain/'
                          '_/credential/Test%20System%20Credential/config.xml'))

        self.assertEqual(
            jenkins_mock.call_args_list[1][0][0].data,
            self.config_xml.encode('utf-8'))

        self._check_requests(jenkins_mock.call_args_list)


class JenkinsListCredentialConfigTest(JenkinsCredentialTestBase):

    @patch.object(jenkins.Jenkins, 'jenkins_open')
    def test_simple(self, jenkins_mock):
        credentials_to_return = [{'id': 'Test System Credential'}]
        jenkins_mock.side_effect = [
            json.dumps({'credentials': [{'id': 'Test System Credential'}]}),
        ]
        credentials = self.j.list_system_credentials()
        self.assertEqual(credentials, credentials_to_return)
        self.assertEqual(
            jenkins_mock.call_args_list[0][0][0].url,
            self.make_url('credentials/store/system/domain/'
                          '_/api/json?tree=credentials[id]'))
        self._check_requests(jenkins_mock.call_args_list)
