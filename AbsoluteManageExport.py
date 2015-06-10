#!/usr/bin/env python
#
# Copyright 2014 Thomas Burgin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os,   \
       uuid,  \
       shutil, \
       hashlib, \
       datetime, \
       sqlite3,   \
       plistlib,   \
       subprocess


from Foundation import  NSArray,     \
                        NSDictionary, \
                        NSUserName,    \
                        NSHomeDirectory

from os.path import expanduser
from CoreFoundation import CFPreferencesCopyAppValue
from autopkglib import Processor, ProcessorError

__all__ = ["AbsoluteManageExport"]


class AbsoluteManageExport(Processor):
    '''Take as input a pkg or executable and a SDPackages.ampkgprops (plist config) to output a .amsdpackages for use in Absolute Manage.
        If no SDPackages.ampkgprops is specified a default config will be generated'''

    description = __doc__

    input_variables = {
        'source_payload_path': {
            'description': 'Path to a pkg or executable',
            'required': True,
        },
        'dest_payload_path': {
            'description': 'Path to the exported .amsdpackages',
            'required': True,
        },
        'sdpackages_ampkgprops_path': {
            'description': 'Path to a plist config for the Software Package to be used in Absolute Manage',
            'required': False,
        },
        'sd_name_prefix': {
            'description': 'Define a prefix for the package to follow naming conventions',
            'required': False,
        },
        'payload_name_prefix': {
            'description': 'Define a prefix for the payload to follow naming conventions',
            'required': False,
        },
        'import_abman_to_servercenter': {
            'description': 'Imports autopkg .pkg result to AbMan',
            'required': False,
        },
        'add_s_to_availability_date': {
            'description': 'Input additional number of seconds to be added to the AvailabilityDate on the default ampkgprops',
            'required': False,
        },

    }

    output_variables = {}
    appleSingleTool = "/Applications/LANrev Admin.app/Contents/MacOS/AppleSingleTool"
    sdpackages_template = {'SDPackageExportVersion': 1, 'SDPayloadFolder': 'Payloads', 'SDPackageList': [{'IsNewEntry': False, 'OptionalData': [], 'RequiresLoggedInUser': False, 'InstallTimeEnd': [], 'AllowOnDemandInstallation': False, 'InstallTime': [], 'AutoStartInstallationMinutes': [], 'SoftwarePatchIdentifier': [], 'RestartNotificationNagTime': [], 'PlatformArchitecture': 131071, 'ExecutableSize': 0, 'ResetSeed': 1, 'Priority': 2, 'WU_LanguageCode': [], 'WU_SuperseededByPackageID': [], 'WU_IsUninstallable': [], 'WU_LastDeploymentChangeTime': [], 'IsMacOSPatch': False, 'UploadStatus': [], 'id': 0, 'RequiresAdminPrivileges': False, 'InstallationContextSelector': 2, 'SoftwareSpecNeedToExist': True, 'MinimumOS': 0, 'Description': '', 'AllowOnDemandRemoval': False, 'RetrySeed': 1, 'MaximumOS': 0, 'SoftwarePatchStatus': 0, 'IsMetaPackage': False, 'SoftwarePatchSupportedOS': [], 'ScanAllVolumes': False, 'DontInstallOnSlowNetwork': False, 'ShowRestartNotification': False, 'SelfHealingOptions': [], 'AllowDeferMinutes': [], 'last_modified': '', 'SoftwarePatchRecommended': [], 'UserContext': '', 'EnableSelfHealing': False, 'InstallationDateTime': [], 'AllowToPostponeRestart': False, 'PayloadExecutableUUID': '', 'WU_IsBeta': [], 'OSPlatform': 1, 'RequiresRestart': 0, 'Name': '', 'FindCriteria': {'Operator': 'AND', 'Value': [{'Operator': 'AND', 'Value': [{'Operator': '=', 'Units': 'Minutes', 'Property': 'Name', 'Value2': '', 'Value': ''}]}, {'UseNativeType': True, 'Value': True, 'Units': 'Minutes', 'Value2': '', 'Operator': '=', 'Property': 'IsPackage'}, {'UseNativeType': True, 'Value': True, 'Units': 'Minutes', 'Value2': '', 'Operator': '=', 'Property': 'IsApplication'}]}, 'SDPayloadList': [{'IsNewEntry': 0, 'OptionalData': [], 'SelectedObjectIsExecutable': True, 'Description': '', 'ExecutableName': '', 'ExecutableSize': 0, 'TransferExecutableFolder': False, 'id': 0, 'SourceFilePath': '', 'last_modified': '', 'PayloadOptions': 0, 'UniqueID': '', 'IsVisible': True, 'UploadStatus': 2, 'MD5Checksum': '', 'Name': ''}], 'DisplayProgressDuringInstall': False, 'ContinueInstallationAfterFailure': False, 'UserInteraction': 1, 'WarnAboutSlowNetwork': False, 'InstallTimeOptions': 1, 'WU_IsMandatory': [], 'DownloadPackagesBeforeShowingToUser': False, 'PackageType': 1, 'WU_Deadline': [], 'SoftwarePatchVersion': [], 'WU_DeploymentAction': [], 'TargetInstallationVolume': '', 'KeepPackageFileAfterInstallation': False, 'MD5Checksum': [], 'TransferExecutableFolder': [], 'WU_SuperseededByPackageName': [], 'StagingServerOption': 1, 'ExecutableOptions': '', 'WU_UninstallationBehaviorImpact': [], 'ExecutableName': [], 'ExecutableServerVolume': [], 'DontInstallIfUserIsLoggedIn': False, 'SourceFilePath': [], 'UserContextPassword': '', 'AvailabilityDate': datetime.datetime.today(), 'WU_InstallationBehaviorImpact': [], 'PostNotificationAutoClose': [], 'UniqueID': '', 'UseSoftwareSpec': False, 'ExecutablePath': [], 'IsWindowsPatch': False}]}
    open_exe = "/usr/bin/open"
    BUNDLE_ID = "com.poleposition-sw.lanrev_admin"

    
    def get_pref(self, key, domain=BUNDLE_ID):
        """Return a single pref value (or None) for a domain."""
        value = CFPreferencesCopyAppValue(key, domain) or None
        # Casting NSArrays and NSDictionaries to native Python types.
        # This a workaround for 10.6, where PyObjC doesn't seem to
        # support as many common operations such as list concatenation
        # between Python and ObjC objects.
        if isinstance(value, NSArray):
            value = list(value)
        elif isinstance(value, NSDictionary):
            value = dict(value)
        return value
    
    
    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    
   
    def md5_for_file(self, path, block_size=256*128):
        md5 = hashlib.md5()
        with open(path,'rb') as f: 
            for chunk in iter(lambda: f.read(block_size), b''): 
                 md5.update(chunk)
        return md5.hexdigest()

    def check_sd_payload(self, exe_name):
        self.output("[+] Checking if [%s] exists in SDCaches.db" % self.sdpackages_template['SDPackageList'][0]['Name'])
        
        self.output("[+] Attempting to build SDCaches.db path")
        am_server     = self.get_pref("ServerAddress")
        self.output("[+] Current AM Server [%s]" % am_server)
        
        try:
            database_path = expanduser(self.get_pref("DatabaseDirectory"))
        except:
            pass

        if not database_path:
            database_path = NSHomeDirectory() + "/Library/Application Support/LANrev Admin/Database/"
            self.output("[+] Using default database path [%s]" % database_path)
        else:
            if not database_path[-1] == "/":
                database_path = expanduser(database_path + "/")
            self.output("[+] Using override database path [%s]" % database_path)


        servers_list = os.listdir(database_path)
        
        for e in servers_list:
            if am_server in e:
                database_path = database_path + e + "/SDCaches.db"
                break

        self.output("[+] Full path to database [%s]" % database_path)

        conn = sqlite3.connect(database_path)
        conn.row_factory = self.dict_factory
        c = conn.cursor()
        sd_packages = c.execute("select * from 'sd_payloads_latest'").fetchall()
        c.close()
        conn.close()

        for e in sd_packages:
            if e["ExecutableName"] == exe_name:
                self.output("[+] [%s] already exists in Absolute Manage Server Center" % exe_name)
                return True

        return False


    def export_amsdpackages(self, source_dir, dest_dir, am_options, sd_name_prefix, payload_name_prefix, sec_to_add, import_pkg):
        
        unique_id = str(uuid.uuid4()).upper()
        unique_id_sd = str(uuid.uuid4()).upper()
        self.output("[+] unique_id [%s]" % unique_id)
        self.output("[+] unique_id_sd [%s]" % unique_id_sd)

        if sd_name_prefix == None:
            sd_name_prefix = ""

        if payload_name_prefix == None:
            payload_name_prefix = ""

        if os.path.exists(dest_dir):
            self.output("[+] dest_dir [%s] exists. Removing it." % dest_dir)
            shutil.rmtree(dest_dir)

        try:
            self.output("[+] Creating [%s]" % dest_dir)
            os.mkdir(dest_dir)
            self.output("[+] Creating [%s/Payloads]" % dest_dir)
            os.mkdir(dest_dir + "/Payloads")

        except OSError, err:
            if os.path.exists(dest_dir):
                pass
            else:
                self.output("[+] Failed to create [%s] Please check your permissions and try again. Error [%s]"  (dest_dir, err))

        try:
            subprocess.check_output([self.appleSingleTool, "encode", "-s", source_dir, "-t", dest_dir + "/Payloads/" + unique_id, "-p", "-x", "-z", "3"])
            self.output("[+] Exported [%s] to [%s]" % (source_dir, dest_dir))

        except (subprocess.CalledProcessError, OSError), err:
            self.output("[!] Please make sure [%s] exists" %  appleSingleTool)
            raise err

        try:
            if os.path.exists(am_options):
                shutil.copyfile(am_options, dest_dir + "/SDPackages.ampkgprops")
            else:
                plistlib.writePlist(self.sdpackages_template, dest_dir + "/SDPackages.ampkgprops")
        except (TypeError, OSError):
            plistlib.writePlist(self.sdpackages_template, dest_dir + "/SDPackages.ampkgprops")

        try:
            executable_size = subprocess.check_output(["/usr/bin/stat", "-f%z", source_dir])
            md5_checksum = self.md5_for_file(dest_dir + "/Payloads/" + unique_id)

        except (subprocess.CalledProcessError, OSError), err:
            raise err

        self.sdpackages_template = plistlib.readPlist(dest_dir + "/SDPackages.ampkgprops")

        self.sdpackages_template['SDPackageList'][0]['Name'] = sd_name_prefix + source_dir.split("/")[-1].strip(".pkg")
        self.sdpackages_template['SDPackageList'][0]['PayloadExecutableUUID'] = unique_id
        self.sdpackages_template['SDPackageList'][0]['UniqueID'] = unique_id_sd
        self.sdpackages_template['SDPackageList'][0]['ExecutableSize'] = int(executable_size)
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['ExecutableName'] = source_dir.split("/")[-1]
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['ExecutableSize'] = int(executable_size)
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['MD5Checksum'] = md5_checksum
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['Name'] = payload_name_prefix + source_dir.split("/")[-1].strip(".pkg")
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['SourceFilePath'] = source_dir
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['UniqueID'] = unique_id
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['last_modified'] = ""

        ## Add defined sec to AvailabilityDate
        date = datetime.datetime.today()
        date = date + datetime.timedelta(0, sec_to_add)
        self.sdpackages_template['SDPackageList'][0]['AvailabilityDate'] = date

        plistlib.writePlist(self.sdpackages_template, dest_dir + "/SDPackages.ampkgprops")

        if import_pkg and not self.check_sd_payload(source_dir.split("/")[-1]):
            self.output("[+] Attemting to upload [%s] to Absolute Manage Server Center" % dest_dir)
            try:
                subprocess.check_output([self.open_exe, "lanrevadmin://importsoftwarepackage?packagepath=" + dest_dir])
                subprocess.check_output([self.open_exe, "lanrevadmin://commitsoftwarepackagechanges"])
            except (subprocess.CalledProcessError, OSError), err:
                raise err
        else:
            self.output("[+] Nothing uploaded to Absolute Manage")


    def main(self):
        source_payload = self.env.get('source_payload_path')
        dest_payload = self.env.get('dest_payload_path')
        sdpackages_ampkgprops = self.env.get('sdpackages_ampkgprops_path')
        sd_name_prefix = self.env.get('sd_name_prefix')
        payload_name_prefix = self.env.get('payload_name_prefix')
        import_pkg = self.env.get('import_abman_to_servercenter')
        try:
            sec_to_add = int(self.env.get('add_s_to_availability_date'))
        except (ValueError, TypeError):
            self.output("[+] add_s_to_availability_date is not an int. Reverting to default of 0")
            sec_to_add = 0

        self.export_amsdpackages(source_payload, dest_payload, sdpackages_ampkgprops, sd_name_prefix, payload_name_prefix, sec_to_add, import_pkg)


if __name__ == '__main__':
    processor = AbsoluteManageExport()
    processor.execute_shell()
