import micropython
import time
from filefifo import Filefifo
from fifo import Fifo
from machine import ADC, Pin, I2C
from ssd1306 import SSD1306_I2C
import network
import urequests as requests 
import ujson
from time import sleep
from umqtt.simple import MQTTClient
import mip


interval_between_data_points = 40 # in ms
sample_count_between_30_seconds = 30000 / interval_between_data_points # total 600 samples


WIFI_NAME="KMD652_Group_11"
WIFI_PASS="Group_11_FSM"


#MQTT_BROKER = "mqtt-dashboard.com"
#MQTT_TOPIC = "HRV_DATA"
#MQTT_CLIENT_ID = "RPI_PICO_GROUP_11"
MQTT_BROKER = "192.168.11.253" #provide the mqtt server  ip address
MQTT_TOPIC = "pico/test" #provide the topic
MQTT_CLIENT_ID = "KMD652_Group_11"


################# OLED INIT #######################

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)
oled.fill(0)

###################################################

################### HR SENSOR #####################
        
hr_sensor =  ADC(Pin(26, Pin.IN))
    
def get_data(delay=0):
    if delay >0:
        time.sleep(delay/1000)
    
    return hr_sensor.read_u16()

###################################################


class Encoder:
    def __init__(self, rot_a, rot_b):
        self.a = Pin(rot_a, mode = Pin.IN, pull = Pin.PULL_UP)
        self.b = Pin(rot_b, mode = Pin.IN, pull = Pin.PULL_UP)
        self.fifo = Fifo(30, typecode = 'i')
        self.a.irq(handler = self.handler, trigger = Pin.IRQ_RISING, hard = True)
    def handler(self, pin):
        if self.b():
            self.fifo.put(-1)
        else:
            self.fifo.put(1)


############ Operation IO variables ######
button = Pin(12, mode = Pin.IN, pull = Pin.PULL_UP)
rot = Encoder(10, 11)
##########################################


    
def send_to_mqtt(hrv_data):
    
    message = ujson.dumps(hrv_data.to_json())

    try:
        display_centered_message("Sending data", "to Mqtt")

         # Create MQTT client instance
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)

        # Connect to MQTT broker
        mqtt_client.connect()

        # Publish message
        mqtt_client.publish(MQTT_TOPIC, message)

        # Disconnect from MQTT broker
        mqtt_client.disconnect()
        time.sleep(1)

    except Exception as e:
        display_centered_message("Failed to","Send data","to Mqtt!")
        time.sleep(2)
        

def connect_to_internet():
    global  WIFI_NAME, WIFI_PASS
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_NAME, WIFI_PASS)

    retry_count = 20   # Try to connect up until 20 second otherwise it will fail.
    while not wlan.isconnected() and retry_count>0:
        the_dots=""
        if retry_count%3 ==0:
            the_dots = "." 
        if retry_count%3 ==2:
            the_dots = ".."
        if retry_count%3 ==1:
            the_dots = "..."
        display_centered_message("Checking WiFi",the_dots)
        
        time.sleep(.5)
        retry_count -= 1
    
    if not wlan.isconnected() :
        display_centered_message("Unable to","Connect to","the Internet")
        
        
    return wlan.isconnected()


# This class stores HRV record
class HRVData:
    def __init__(self, calculation_type="P", mean_hr=0, mean_ppi=0, rmssd=0, sdnn=0, sns=0.0, pns=0.0):
        self._mean_hr = mean_hr
        self._mean_ppi = mean_ppi
        self._rmssd = rmssd
        self._sdnn = sdnn
        self._sns = sns
        self._pns = pns
        self._calculation_type = calculation_type
        
    def get_calculation_type(self):
        return self._calculation_type
        
    def get_mean_hr(self):
        return self._mean_hr

    def get_mean_ppi(self):
        return self._mean_ppi

    def get_rmssd(self):
        return self._rmssd

    def get_sdnn(self):
        return self._sdnn

    def get_sns(self):
        return self._sns

    def get_pns(self):
        return self._pns

    def to_json(self):
        return {
            "calculation_type": self._calculation_type,
            "mean_hr": self._mean_hr,
            "mean_ppi": self._mean_ppi,
            "rmssd": self._rmssd,
            "sdnn": self._sdnn,
            "sns": self._sns,
            "pns": self._pns
        }


def push_to_history(hrv_data):
    if len(history_array)<6:
        history_array.append(hrv_data)
    else:
        for i in range(len(history_array)-1):
            history_array[i] = history_array[i+1]
        history_array[5] = hrv_data
    

def print_hrv(hrv_data):
    oled.fill(0)
    
    display_text(f"MEAN HR: {hrv_data.get_mean_hr()}",1)
    display_text(f"MEAN PPI: {hrv_data.get_mean_ppi()}",2)
    display_text(f"RMSSD: {hrv_data.get_rmssd()}",3)
    display_text(f"SDNN: {hrv_data.get_sdnn()}",4)
    display_text(f"SNS: {hrv_data.get_sns()}",5)
    display_text(f"PNS: {hrv_data.get_pns()}",6)

    oled.show()
    

def calculate_hrv(PPI_ARRAY, BPM_ARRAY):
    RMSSD = 0
    SDNN = 0
 
    MEAN_PPI = 0
    MEAN_BPM = 0
    
    ppi_sum = 0
    bpm_sum = 0

    for i in range(len(PPI_ARRAY)):
        ppi_sum += PPI_ARRAY[i]
        bpm_sum += BPM_ARRAY[i]
 
    
    MEAN_PPI = ppi_sum//len(PPI_ARRAY)
    MEAN_BPM = bpm_sum//len(PPI_ARRAY)

    sqr_sum_RMSSD = 0
    sqr_sum_SDNN = 0

    i = 0
    while i < len(PPI_ARRAY):
        if i < len(PPI_ARRAY) - 1:
            sqr_sum_RMSSD += (PPI_ARRAY[i + 1] - PPI_ARRAY[i]) ** 2

        sqr_sum_SDNN += (PPI_ARRAY[i] - MEAN_PPI) ** 2
        i += 1

    RMSSD = round((sqr_sum_RMSSD / (len(PPI_ARRAY) - 1)) ** (1 / 2), 0)
    SDNN = round((sqr_sum_SDNN / (len(PPI_ARRAY) - 1)) ** (1 / 2), 0)
    
    return HRVData ("P",MEAN_BPM,MEAN_PPI,RMSSD,SDNN)######################################### ADD SNS PNS HERE


def calculate_threshold(data_20, sample, queue_size):
    sum_data = 0
    max_val = sample
    min_val = sample
    threshold = 0
    
    if len(data_20) >= queue_size:
        for i in range (len(data_20)-1):
            data_20[i] = data_20[i+1]
            if max_val > data_20[i] :
                max_val = data_20[i]
            if min_val < data_20[i] :
               min_val = data_20[i]
               
        data_20[queue_size-1] = sample
        threshold = (max_val + min_val )/2
    else:
        data_20.append(sample)
        
    return threshold, max_val, min_val  # using max and min value to plot data more accurately

def process_data_for_latest_30_second(is_kubios):
    global calculation_frame, HRV_calculated

    previous_peak_time = 0

    PPI_ARRAY = []
    BPM_ARRAY = []
    data_20 = []

    previous_slop_sign = 0
    slope = 0
    threshold=0
    
    previous_datapoint = None
    
    for frame_sample in calculation_frame:  # calculation_frame is an array of two value Tuple. where 1st one represents time and second one represents value
        # print(threshold,value)
    
        frame_time = frame_sample[0]
        value = frame_sample[1]

        threshold, _, _ = calculate_threshold(data_20,value,20)
        
        if threshold ==0:
            continue
        
        if value > threshold:
            if previous_datapoint != None:
                slope = (value - previous_datapoint)
                if previous_slop_sign >= 0 and slope < 0:
                    ppi = frame_time - previous_peak_time
                    if ppi >= 250 and ppi <= 2000:
                        bpm = int(60000 / ((ppi)))
                        PPI_ARRAY.append(ppi)
                        BPM_ARRAY.append(bpm)
                        previous_peak_time = frame_time
                    
            previous_datapoint = value
            previous_slop_sign = slope
 
 
 
    if len(PPI_ARRAY) == 0:
        display_centered_message("Unable to", "collect enough", "usable data")
        time.sleep(2)
        display_centered_message("Please adjust", "finger your", "and", "try again!")
        HRV_calculated = True
        return
    
            
    if not is_kubios:
        hrv_data = calculate_hrv(PPI_ARRAY,BPM_ARRAY)
        
        push_to_history(hrv_data)
        if connect_to_internet():
            send_to_mqtt(hrv_data)
        
        print_hrv(hrv_data)
        HRV_calculated = True
    else:
        sending_data_to_kubios(PPI_ARRAY)
    

previous_sample = 0
previous_peak_time_plot = 0
plot_HR = 0
plot_PPI = 1 
previous_slop_sign_running = 0
data_20_for_plot = []

def calculate_running_data():
    global data_20_for_plot, current_time_plot,previous_slop_sign_running, previous_sample, previous_peak_time_plot,plot_HR,plot_PPI
       
    sample = get_data(12)   # delaying 12 ms. the calculation operation takes 28ms so total delay becomes 40ms: 40ms avoid noises and gives clear peaks for calculation.
       
    threshold, max_val, min_val = calculate_threshold(data_20_for_plot, sample,20)
    
    bpm = 0
    ppi = 0
    
    if threshold !=0:
        if sample > threshold:
            if previous_sample != None:
                slope = (sample - previous_sample)
                if previous_slop_sign_running >= 0 and slope < 0:
                    ppi = current_time_plot - previous_peak_time_plot
                    if ppi >= 250 and ppi <= 2000:    # 30- 240 HR otherwise invalid 
                        bpm = int(60000 / ((ppi)))

                    previous_peak_time_plot = current_time_plot  # Storing for next calculation

            previous_sample = sample           # Storing for next calculation
            previous_slop_sign_running = slope # Storing for next calculation
    
    if bpm != 0 and ppi !=0:
        plot_PPI = ppi
        plot_HR = bpm
 
    plot_data(sample, max_val, min_val, threshold, plot_HR, plot_PPI)
    
    current_time_plot = current_time_plot + 40


x1 = 0
y1 = 34
x2 = 0
y2 = 34
def plot_data(sample, max_val, min_val,threshold, bpm,ppi):
    global x1, y1, x2, y2
    
    scaled_max = max_val-min_val
    scaled_sample = sample - min_val
    scaled_threshold = threshold - min_val
    
    x2 += 2
    if x2> 128:
       x2 = 0
       
       
    oled.fill_rect(0, 0, oled_width, 10, 0)  # Clearing top Heading text 
  
    oled.fill_rect(x1, 0, 4, oled_height, 0)  # Clearing vartical line 

    if threshold == 0:
        oled.text(f"Calibrating ...", 0, 0)
    else:
        y2 = 25*scaled_sample//scaled_max + 25
        oled.text(f"HR: {bpm}, {ppi}ms", 0, 0)
    
    if(x2>x1) :     # we are avoiding back to front line when x2 beocmes zero again.
        oled.line(x1, y1, x2, y2, 4)     # drawing line between two points

    x1 = x2
    y1 = y2
    
    oled.show()
    

def operation_1_HR():
    global current_time_plot
    
    if HR_measure_started == False:        
        current_time_plot = 0
    else:
        calculate_running_data()
   

HRV_calculated = False
def operation_2_3_HRV(is_kubios):
    global current_time        
    
    if HRV_calculated:
        return
    sample = get_data(interval_between_data_points)

    remaining = 0
    
    frame_length = len(calculation_frame)
    
    if len(calculation_frame) == sample_count_between_30_seconds:        
        display_centered_message("Analyzing ...")
        process_data_for_latest_30_second(is_kubios)
    else:
        calculation_frame.append((current_time, sample))
        remaining = (30000-frame_length*interval_between_data_points)
        if remaining%1000 ==0:
            display_centered_message("Collecting ...",str(remaining//1000))   # remaining mili second to second conversion
            

    # Update Data
    current_time = current_time + interval_between_data_points
    

def sending_data_to_kubios(data):    # It is taking 30 second PPI_ARRAY extracted from our collected data
    global HRV_calculated
    
    if not connect_to_internet() :  
        HRV_calculated = True
    else:
        try:
            APIKEY = "pbZRUi49X48I56oL1Lq8y8NDjq6rPfzX3AQeNo3a" 
            CLIENT_ID = "3pjgjdmamlj759te85icf0lucv" 
            CLIENT_SECRET = "111fqsli1eo7mejcrlffbklvftcnfl4keoadrdv1o45vt9pndlef" 
            TOKEN_URL = "https://kubioscloud.auth.eu-west-1.amazoncognito.com/oauth2/token" 

            response = requests.post( 
                url = TOKEN_URL, data = 'grant_type=client_credentials&client_id={}'.format(CLIENT_ID), 
                headers = {'Content-Type':'application/x-www-form-urlencoded'}, auth = (CLIENT_ID, CLIENT_SECRET)) 
            response = response.json()  
            access_token = response["access_token"]  

            data_set = {
                "type": "RRI",
                "data": data,
                "analysis": {
                "type": "readiness"}
                }

            response = requests.post( url = "https://analysis.kubioscloud.com/v2/analytics/analyze", 
                headers = { "Authorization": "Bearer {}".format(access_token), 
                 "X-Api-Key": APIKEY }, json = data_set)  
            response = response.json()
            
            hrv_data = HRVData ("K",int(response['analysis']['mean_hr_bpm']),
                                int(response['analysis']['mean_rr_ms']),
                                int(response['analysis']['rmssd_ms']),
                                int(response['analysis']['sdnn_ms']),
                                float(response['analysis']['sns_index']),
                                float(response['analysis']['pns_index']))
            
            push_to_history(hrv_data)
            send_to_mqtt(hrv_data)
            print_hrv(hrv_data)
            HRV_calculated = True
        except Exception as e:
            display_centered_message("Failed to","get response","from Kubios!")
            HRV_calculated = True

        
        
        
      

def operation_3_History(pointer):
    global history_showed
    
    if len(history_array) == 0:
        display_centered_message("History","Not Found!")
        history_showed = True
    else:
        oled.fill(0)
        line_gap = 10
        for i in range(len(history_array)):
            oled.text(generate_selection_line(f"{i+1}.History ({history_array[i].get_calculation_type()})", i==pointer), 0, line_gap*i)
        oled.show()



def generate_selection_line(text, is_selected):
    led_line = "" #blank string
    
    if is_selected:
        led_line += "["
    else:
        led_line += " "
            
    led_line +=  text
    
    if is_selected:
        led_line += " ]"
        
    return led_line

def display_centered_text(text, line):
    # Calculate text position
    text_width = len(text) * 8  # Each character is 8 pixels wide for the default font
    x = (oled_width - text_width) // 2
    y = (line-1)*10  

    # Display text
    oled.text(text, x, y, 1)
    
def display_centered_message(*messageArray):
    oled.fill(0)
    line_count = len(messageArray)
    space_count = 0
    if line_count <5:
        space_count = (6-line_count)//2
        
    for i in range(6):
        if i <space_count:
            display_centered_text("",i+1)
        else:
            if(i-space_count<line_count):
                display_centered_text(messageArray[i-space_count],i+1)
    
    oled.show()
            
def display_text(text, line):
    # Calculate text position
    x = 1
    y = (line-1)*10

    # Display text
    oled.text(text, x, y, 1)


def open_menu():
    # Clear the display
    oled.fill(0)
    
    line_gap = 18
    oled.text(generate_selection_line("1. Measure HR", selected==0), 0, 0)
    oled.text(generate_selection_line("2. Basic HRV", selected==1), 0, line_gap*1)
    oled.text(generate_selection_line("3. Kubios", selected==2), 0, line_gap*2)
    oled.text(generate_selection_line("4. History", selected==3), 0, line_gap*3)
    
    oled.show()




################## Global State Variables #######################
current_time = 0
current_time_plot = 0
calculation_frame = []
history_array = []
selected = 0
history_selected = 0
operation_status = 0
HR_measure_started = False
button_pre_val = 1
history_showed = False
#################################################################


while True:

    if operation_status == 0:
        open_menu()
    elif operation_status == 1:
        operation_1_HR()
    elif operation_status == 2:
        operation_2_3_HRV(False)
    elif operation_status == 3:
        operation_2_3_HRV(True)
    elif operation_status == 4:
        if history_showed == False:
            operation_3_History(history_selected)


    # Only executed when rotary knob is rotated
    while rot.fifo.has_data():
        rotation = rot.fifo.get()
        if operation_status==0 :
            selected = selected + rotation
            if selected < 0:
                selected = 0
            if selected > 3:
                selected = 3
        if operation_status==4 :
            history_selected = history_selected +  rotation

            if  history_selected < 0:
                history_selected = 0
                
            if history_selected > len(history_array)-1:
                history_selected = len(history_array)-1
    

    button_val = button.value()
    # Only executed when button is clicked
    if button_pre_val ==0 and button_val==1:
        button_pre_val = button_val
        
        if operation_status == 0:
            if selected == 0:
                operation_status = 1
                HR_measure_started = False
                continue
            elif selected == 1:
                operation_status = 2
                current_time = 0
                calculation_frame = []
                HRV_calculated = False
                continue
            elif selected == 2:
                operation_status = 3
                current_time = 0
                calculation_frame = []
                HRV_calculated = False
                continue
            elif selected == 3:
                operation_status = 4
                history_selected = 0
                history_showed = False
                continue
    
        if operation_status == 1:
            if HR_measure_started == False:
                HR_measure_started = True
                data_20_for_plot = []
                oled.fill(0)
            else:
                operation_status = 0
            continue
        elif operation_status == 2 or operation_status == 3:
            if HRV_calculated == True:
                operation_status = 0
                continue
        elif operation_status == 4:
            if history_showed == False:
                if len(history_array) > 0:
                    print_hrv(history_array[history_selected])
                    history_showed = True
                    continue
            else:
                operation_status = 0
                continue
        
    button_pre_val = button_val

   