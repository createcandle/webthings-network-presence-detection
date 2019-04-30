"""Presence Detection adapter for Mozilla WebThings Gateway."""

import time
import threading
import subprocess
import json
import re


from datetime import datetime, timedelta
from gateway_addon import Adapter, Database

from .presence_device import presenceDevice


# for macvendor
import os.path
import os

OUI_FILE = 'oui.txt'
SEPARATORS = ('-', ':')
BUFFER_SIZE = 1024 * 8

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


_POLL_INTERVAL = 60   # 60 seconds between polling



class presenceAdapter(Adapter):
    """Adapter for MySensors"""

    def __init__(self, verbose=True):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        print("initialising adapter from class")
        self.pairing = False
        self.name = self.__class__.__name__
        Adapter.__init__(self, 'network-presence', 'network-presence', verbose=verbose)
        print("Adapter ID = " + self.get_id())
        
        self.memory_in_weeks  = 10
        
        self.add_from_config()
        
        
        self.filename = 'found_devices.json' # This stores the previously found devices.

        # make sure the file exists:
        try:
            with open(self.filename) as file_object:

                print("Loading json..")
                self.previously_found = json.load(file_object)

                #print("Previously found items: = " + str(self.previously_found))

        except IOError:
            self.previously_found = {}
            print("Failed to load JSON file")
            file = open(self.filename, 'w')
            file.close()
            
            
        # Remove devices that have not been seen in a long time
        self.prune() 

        # Present all devices to the gateway
        for key in self.previously_found:
            item = self.previously_found[key]
            self._add_device(str(key), str(item['name']), '') # adding the device

            
            
        # Once a minute start the scan process
        t = threading.Thread(target=self.poll)
        t.daemon = True
        t.start()



    def unload(self):
        print("adapter is being unloaded")
        self.save_to_json()
        t.stop
        



    def poll(self):
            """Poll the device for changes."""
            while True:
                self.scan()
                time.sleep(_POLL_INTERVAL)



    def scan(self):
        print()
        print("Scanning..")
        
        shouldSave = False # should the found_devices list be saves to a file? We only do this if new devices have been found during this scan.
        now = datetime.now()
        
        #print(str( self.previously_found.values() ))
        
        # First we add any new devices on the network.
        try:
            output = str(subprocess.check_output("sudo arp", shell=True).decode()) # .decode('ISO-8859-1')

            print(output)
            for line in output.split('\n'):
                print()
                #print("line: " + str(line))
                line = str(line)
                
                ip_addresses = re.findall( r'[0-9]+(?:\.[0-9]+){3}', line)
                #print("ip address(es) found: " + str(ip_addresses))
                
                
                mac_addresses = re.findall(r'(?:[0-9a-fA-F]:?){12}', line)
                #print("mac address(es) found: " + str(mac_addresses))

                if len(ip_addresses) == 0:
                    #print("ip address was empty")
                    ip_address = ''
                else:
                    ip_address = ip_addresses[0]

                if len(mac_addresses) == 0:
                    #print("No useful data")
                    
                    if "incomplete" in line:
                        mac_address = "unknown" + str(ip_address)
                        vendorName = "Presence - Unknown device"
                    else:    
                        continue
                else:
                    mac_address = mac_addresses[0]
                    vendorName = "Presence - " + str(get_vendor(mac_address).split(',', 1)[0]) # Get the vendor name, and shorten it. It removes everything after the comma. Thus "Apple, inc" becomes "Apple"
                
                print("Initial vendor name: " + str(vendorName))
                
                mac_address = mac_address.replace(":","")
                #print("cleaned mac: " + str(mac_address))
                
                try:
                    if mac_address in self.previously_found:
                        print(" -mac address already known")
                        #print(str( self.previously_found[mac_address]['lastseen'] ))
                        self.previously_found[mac_address]['lastseen'] = datetime.timestamp(now)
                        # should now update the last seen time stamp.
                        print("- last seen date updated")
                        pass
                    else:
                        shouldSave = True
                        
                        i = 2 # We skip "1" as a number. So we will get names like "Apple" and then "Apple 2", "Apple 3", and so on.
                        possibleName = vendorName
                        could_be_same_same = True
                        
                        while could_be_same_same is True: # We check if this name already exists in the list of previously found devices.
                            could_be_same_same = False
                            for item in self.previously_found.values():
                                if possibleName == item['name']: # The name already existed in the list, so we change it a little bit and compare again.
                                    could_be_same_same = True
                                    #print("names collided")
                                    possibleName = vendorName + " " + str(i)
                                    i += 1
                                    
                        self.previously_found[str(mac_address)] = { 'name': str(possibleName),'lastseen': datetime.timestamp(now) }
                        
                        self._add_device(str(mac_address), str(possibleName), str(ip_address)) # The device did not exist yet, so we're creating it.
                        
                        print("Added new device:" + str(possibleName))

                except Exception as ex:
                    print("Error comparing to previous mac addresses list: " + str(ex))

        except Exception as ex:
            print("Error while scanning: " + str(ex))

        #print(str(self.previously_found))
        if shouldSave is True:
            self.save_to_json()
        
        
        # Secondly, we go over the list of all previously found devices, and check their last-update times
        try:
            print()
            #past = datetime.now() - timedelta(hours=1)
            past = datetime.now() - timedelta(minutes=2)
            #print("An hour ago: " + str(past))
            paststamp = datetime.timestamp(past)

            for key in self.previously_found:
                #print("Updating: " + str(key))# + "," + str(item))

                item = self.previously_found[key]
                
                # Check if the device already has a property.
                if not 'lasthour' in self.devices[key].properties:
                    # add the property
                    print("While updating, noticed device did not yet have the lastHour property. Adding now.")
                    self.devices[key].add_boolean_child('lasthour', "Seen in the last hour", True)

                else:
                    if paststamp > item['lastseen']:
                        print(str(key) + " was last seen over an hour ago")
                        self.devices[key].properties['lasthour'].update(False)
                    else:
                        print(str(key) + " was spotted less than an hour ago")
                        self.devices[key].properties['lasthour'].update(True)

        except Exception as ex:
            print("Error while updating: " + str(ex))
                
        # Here we remove devices that haven't been spotted in a long time.
        self.prune()
        
        
        
    def _add_device(self, mac, name, details=''):
        """
        Add the given device, if necessary.

        """
        try:
            print("adapter._add_device: " + str(name))
            device = presenceDevice(self, mac, name, details)
            self.handle_device_added(device)
            print("-Adapter has finished adding new device")

        except Exception as ex:
            print("Error adding new device: " + str(ex))
        
        return




    def prune(self):
        # adding already known devices back into the system. Maybe only devices seen in the last few months?
        
        try:
            print()
            too_old = datetime.now() - timedelta(weeks=self.memory_in_weeks)
            #print("Too old threshold: " + str(too_old))
            too_old_timestamp = datetime.timestamp(too_old)
            
            items_to_remove = []
            
            for key in self.previously_found:
                #print("Updating: " + str(key))# + "," + str(item))
                
                item = self.previously_found[key]
                
                #lastSpottedTime = datetime.strptime('Jun 1 2005  1:33PM', '%b %d %Y %I:%M%p')
                
                if too_old_timestamp > item['lastseen']:
                    print(str(key) + " was too old")
                    items_to_remove.append(key)
                else:
                    #print(str(key) + " was not too old")
                    pass
                    
            if len(items_to_remove):
                for remove_me in items_to_remove:
                    self.previously_found.pop(remove_me, None)
                    #del self.previously_found[remove_me]
                    
        except Exception as ex:
            print("Error pruning: " + str(ex))


    def add_from_config(self):
        """Attempt to add all configured devices."""
        
        try:
            database = Database('presence-adapter')
        except:
            print("config database error")
        
        if not database.open():
            return

        config = database.load_config()
        database.close()

        if not config or 'Memory' not in config:
            return

        self.memory_in_weeks = int(config['Memory'])
        

    def save_to_json(self):
            #print(str(self.previously_found))
        try:
            print()
            print("Saving updated list of found devices to json file")
            if str(self.previously_found) != 'Null' or str(self.previously_found) != 'None':
                with open(self.filename, 'w') as fp:
                    json.dump(self.previously_found, fp)
        except:
            print("Saving to json file failed")



    def cancel_pairing(self):
        """Cancel the pairing process."""
        self.pairing = False
        self.save_to_json()




# I couldn't get the import to work, so I just copied some of the code here:
# It was made by Victor Oliveira (victor.oliveira@gmx.com)


def get_vendor(mac, oui_file=OUI_FILE):
    mac_clean = mac
    for separator in SEPARATORS:
        mac_clean = ''.join(mac_clean.split(separator))

    try:
        int(mac_clean, 16)
    except ValueError:
        raise ValueError('Invalid MAC address.')

    mac_size = len(mac_clean)
    if mac_size > 12 or mac_size < 6:
        raise ValueError('Invalid MAC address.')

    with open(os.path.join(__location__, oui_file)) as file:
        mac_half = mac_clean[0:6]
        mac_half_upper = mac_half.upper()
        while True:
            line = file.readline()
            if line:
                if line.startswith(mac_half_upper):
                    vendor = line.strip().split('\t')[-1]
                    return vendor
            else:
                break


        
        
        