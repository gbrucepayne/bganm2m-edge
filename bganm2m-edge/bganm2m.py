import json
import socket

IP_ADDRESS = '192.168.128.100'
IP_PORT = 1829
BUFFER_SIZE = 1024
BGAN_INTERFACE = 'enp2s0'
BGAN_PASS = 'c0miTERM'
AT_TIME = 'AT+CCLK'
AT_SEND_SMS = 'AT+CMGS='   #<da><CR><text><ctrl-z/ESC>
AT_GNSS = 'AT_IGPS?'   # response format: <lat_deg>,<lng_deg>,<type>,<status>,<time> e.g. _IGPS:  45.28498,-75.84855,3D,allowed,19/12/20,17:52:07
AT_SNR = 'AT_ISIG'   # seems to return integer value not decimal like GUI?
AT_ISATVIS = 'AT_ISATVIS'
AT_ISATCUR = 'AT_ISATCUR?'   # 7,262.0=AMER, 3,64.0, 5,143.5, 6,24.9
AT_PDP = 'AT+CGDCONT?'   # <cid>  e.g. +CGDCONT: 1,"IP","stratos.bgan.inmarsat.com","216.86.247.146",0,0,,,"192.168.128.102",,"212.165.65.67","212.165.65.70"

AT_HNS_INIT = 'AT_ICLCK="AD",0,"{}"'.format(BGAN_PASS)
AT_HNS_BEAM = 'AT_IHBEAM?'

BGAN_SATELLITES = {
  7: { 'name': 'AMER', 'sat': 'I4F3', 'position': 262.0 },
  3: { 'name': 'MEAS', 'sat': 'I4F2', 'position': 64.0 },
  5: { 'name': 'APAC', 'sat': 'I4F1', 'position': 143.5 },
  6: { 'name': 'EMEA', 'sat': 'Alphasat', 'position': 24.9 }
}


def get_at_response(at_command):
  at_command += '\r'
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # The concept below is intended to force a specific physical interface e.g. in case of multiple LAN connections but must be run as root
  # s.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, BGAN_INTERFACE.encode())
  s.connect((IP_ADDRESS, IP_PORT))
  s.send(at_command.encode())
  response = []
  complete = False
  while not complete:
    data = s.recv(BUFFER_SIZE).decode()
    res = data.splitlines()
    for r in res:
      if (r != ''):
        if (r == 'OK' or r == 'ERROR'):
          complete = True
        response.append(r)
  s.close()
  return response


# Try AT command, if no response send AT_INIT
def check_at():
  result = get_at_response('AT')[0]
  if (result == 'ERROR'):
    result = get_at_response(AT_HNS_INIT)[0]
  return result


def get_ut_info():
  result = {
    'manufacturer': get_at_response('AT+CGMI')[0],
    'model': get_at_response('AT+CGMM')[0],
    'revision': get_at_response('AT+CGMR')[0]
  }
  return result


def check_snr():
  snr = float(get_at_response(AT_SNR)[0].replace('_ISIG: ', ''))
  beam = int(get_at_response(AT_HNS_BEAM)[0].replace('_IHBEAM: ', ''))
  if (beam >= 1 and beam <= 19):
    beam_type = 'REGIONAL'
  else:
    beam_type = 'NARROW'
  sat_num = int(get_at_response(AT_ISATCUR)[0].replace('_ISATCUR: ', ''))
  satellite = BGAN_SATELLITES[sat_num]['name']
  # TODO: quality metrics on SNR
  if (beam_type == 'REGIONAL' and snr >= 55.0) or (beam_type == 'NARROW' and snr >= 65.0):
    signal = 'GOOD'
  elif (beam_type == 'REGIONAL' and snr >= 40.0) or (beam_type == 'NARROW' and snr >= 55.0):
    signal = 'MARGINAL'
  else:
    signal = 'POOR'
  result = {
    'satellite': satellite,
    'beam_type': beam_type,
    'beam': beam,
    'snr': snr,
    'signal': signal
  }
  return result
  

def get_pdp_info():
  res = get_at_response(AT_PDP)[0].replace('+CGDCONT: ', '').split(',')
  context = {
    'pdp_context': int(res[0]),
    'context_type': res[1].replace('"', ''),
    'apn': res[2].replace('"', ''),
    'global_ip': res[3].replace('"', '')
  }
  return context


# feel free to alter/add, but do not remove the definition `msg_handler`
def msg_handler(input, module):
    print(json.dumps(input))
    # bgan_password = input['admin_pwd']
    output = {}
    if (check_at() != 'OK'):
      output['error'] = 'AT command failed'
    output.update(get_ut_info())
    output.update(check_snr())
    output.update(get_pdp_info())
    # pass the message to the next module
    if (module != None):
      module.next(output)
    else:
      print(output)
    

# local test only
if __name__ == '__main__':
  msg_handler({'admin_pwd': BGAN_PASS}, None)
