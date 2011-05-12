import slapos.slap, subprocess, os, time
from xml_marshaller import xml_marshaller

class SlapOSControler(object):

  def __init__(self, config, process_group_pid_list=None):
    self.config = config
    self.process_group_pid_list = []
    # By erasing everything, we make sure that we are able to "update"
    # existing profiles. This is quite dirty way to do updates...
    if os.path.exists(config['proxy_database']):
      os.unlink(config['proxy_database'])
    proxy = subprocess.Popen([config['slapproxy_binary'],
      config['slapos_config']], close_fds=True, preexec_fn=os.setsid)
    process_group_pid_list.append(proxy.pid)
    # XXX: dirty, giving some time for proxy to being able to accept
    # connections
    time.sleep(2)
    slap = slapos.slap.slap()
    slap.initializeConnection(config['master_url'])
    # register software profile
    self.software_profile = config['custom_profile_path']
    slap.registerSupply().supply(
        self.software_profile,
        computer_guid=config['computer_id'])
    computer = slap.registerComputer(config['computer_id'])
    # create partition and configure computer
    partition_reference = config['partition_reference']
    partition_path = os.path.join(config['instance_root'], partition_reference)
    if not os.path.exists(partition_path):
      os.mkdir(partition_path)
      os.chmod(partition_path, 0750)
    computer.updateConfiguration(xml_marshaller.dumps({
 'address': config['ipv4_address'],
 'instance_root': config['instance_root'],
 'netmask': '255.255.255.255',
 'partition_list': [{'address_list': [{'addr': config['ipv4_address'],
                                       'netmask': '255.255.255.255'},
                                      {'addr': config['ipv6_address'],
                                       'netmask': 'ffff:ffff:ffff::'},
                      ],
                     'path': partition_path,
                     'reference': partition_reference,
                     'tap': {'name': partition_reference},
                     }
                    ],
 'reference': config['computer_id'],
 'software_root': config['software_root']}))

  def runSoftwareRelease(self, config, environment, process_group_pid_list=None):
    print "SlapOSControler.runSoftwareRelease"
    while True:
      cpu_count = os.sysconf("SC_NPROCESSORS_ONLN")
      os.putenv('MAKEFLAGS', '-j%s' % cpu_count)
      os.environ['PATH'] = environment['PATH']
      slapgrid = subprocess.Popen([config['slapgrid_software_binary'], '-v', '-c',
        #'--buildout-parameter',"'-U -N' -o",
        config['slapos_config']],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        close_fds=True, preexec_fn=os.setsid)
      process_group_pid_list.append(slapgrid.pid)
      slapgrid.wait()
      stdout, stderr = slapgrid.communicate()
      status_dict = {'status_code':slapgrid.returncode,
                     'stdout':stdout,
                     'stderr':stderr}
      return status_dict

  def runComputerPartition(self, config, process_group_pid_list=None):
    print "SlapOSControler.runSoftwareRelease"
    slap = slapos.slap.slap()
    slap.registerOpenOrder().request(self.software_profile,
        partition_reference='testing partition',
        partition_parameter_kw=config['instance_dict'])
    slapgrid = subprocess.Popen([config['slapgrid_partition_binary'],
      config['slapos_config'], '-c', '-v'], close_fds=True, preexec_fn=os.setsid)
    process_group_pid_list.append(slapgrid.pid)
    slapgrid.wait()
    if slapgrid.returncode != 0:
      raise ValueError('Slapgrid instance failed')
