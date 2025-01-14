"""Network presence adapter for WebThings Gateway."""

from gateway_addon import Property

class PresenceProperty(Property):
    """Network presence property type."""

    def __init__(self, device, name, description, value):
        """
        Initialize the object.

        device -- the Device this property belongs to
        name -- name of the property
        description -- description of the property, as a dictionary
        value -- current value of this property
        """
        try:
            Property.__init__(self, device, name, description)

            self.device = device
            self.name = name
            self.description = description
            self.value = value

            self.set_cached_value(value)
            self.device.notify_property_changed(self)
            
            if self.device.adapter.DEBUG:
                print("+ PROPERTY init: " + str(name))
                print("-device id: " + str(self.device._id))
                print("-name: " + str(name))
                print("-description: " + str(description))
                print("-value: " + str(value))
            
        except Exception as ex:
            print("property: could not init. Error: " + str(ex))


    def set_value(self, value):
        """
        Set the current value of the property. This is called when the user uses the gateway UX.

        value -- the value to set
        """
        # Theoretically this is never ever called.
        if self.device.adapter.DEBUG:
            print("property " + str(self.name) + "-> set_value to " + str(value))
        try:
            if self.name == 'data-collection':
                #print("self.device.name = " + str(self.device.name))
                #print("self.device._id = " + str(self.device._id))
                #print("prev found keys: " + str( self.device.adapter.previously_found.keys() ))
                self.device.adapter.previously_found[self.device._id]['data-collection'] = bool(value)
                #self.update(value)
                self.set_cached_value(value)
                self.device.notify_property_changed(self)
                self.device.adapter.save_to_json()
        except Exception as ex:
            print("Error updating data-collection value: " + str(ex))


    def update(self, value):
        """
        Update the current value, if necessary.

        value -- the value to update
        """

        if self.device.adapter.DEBUG:
            print("property -> update to: " + str(value))
        try:
            if value != self.value:
                
                if self.device.adapter.DEBUG:
                    print("-property has updated from  " + str(self.value) + " to "  + str(value))
                #self.set_cached_value_and_notify(self, value) For future version, can then remove both lines below.
                self.set_cached_value(value)
                self.device.notify_property_changed(self)
            else:
                #print("-property was still the same value")
                pass
        except:
            print("Error updating property")
