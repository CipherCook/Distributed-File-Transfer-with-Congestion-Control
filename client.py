import socket
import threading
import time
import hashlib
import matplotlib.pyplot as plt

#10.17.7.134
# UDP_IP = "127.0.0.1"  # IP address of the destination server
UDP_IP = "10.17.6.5"  # IP address of the destination server
UDP_PORT = 9802  # Port number of the destination server

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Data to be sent

message = "SendSize\nReset\n\n"
data = ""
sock.settimeout(0.1)
sock.sendto(message.encode('utf-8'), (UDP_IP, UDP_PORT))

while True:
    try:
        data, addr = sock.recvfrom(4096)
        break
    except socket.timeout as e:
        continue
data_decoded = data.decode()
sz = data_decoded.split()[-1]
sz = int(sz)
tot_size = sz // 1448
if (sz%1448 != 0):
    tot_size+=1

# Send the UDP packet

data = ""
rec_cnt = 0
t_list = []
hmap = {}
tcount = 0
rtt_arr = []
for i in range(20):
    for i in range(0, int(sz), 1448):
        if i in hmap:
            continue
        tcount+=1 #1 burst done
        if (tcount > 20): #BURST SIZE finished
            break
        msg = "Offset: " + str(i) + "\nNumBytes: 1448\n\n"
        print(i)
        if (sz - i < 1448):
            rem = sz%1448
            msg = "Offset: " + str(i) + "\nNumBytes: " + str(rem) + "\n\n"
        start_time = time.time()
        sock.sendto(msg.encode('utf-8'), (UDP_IP, UDP_PORT))
        try:
            data, addr = sock.recvfrom(4096)
            end_time = time.time()
            t_list.append(end_time-start_time)
        except socket.timeout as e:
            continue
print(t_list)
t_list = sorted(t_list)
time_taken_avg = t_list[len(t_list)//2]
print(time_taken_avg)

time_taken_avg = max(time_taken_avg, 0.003)
# Function to listen for incoming messages

# data, addr = sock.recvfrom(4096)  # Buffer size is 4096 bytes

burst_arr = []
time_arr = []

offset_arr = []
offset_time = []

rec_offset_arr = []
rec_offset_time = []

squish_arr = []
squish_time = []

burst_size = 5
sock.settimeout(2*time_taken_avg)
l = []
safe_sz = 1
# t_sleep = 0.005
starting_time = time.time()
not_complete = True
ewma_alpha = 0.1
total_lost = 0
while (not_complete):
    not_complete = False
    sent_count = 0
    # time.sleep(t_sleep)
    time.sleep((9/burst_size)*time_taken_avg)
    #BURST STARTS HERE
    
    for i in range(0, int(sz), 1448):
        if i in hmap:
            continue
        else:
            not_complete = True
        print("Asked for ", i) 
        offset_arr.append(i)
        offset_time.append(1000*(time.time() - starting_time))
        sent_count+=1 #1 burst done
        if (sent_count > burst_size): #BURST SIZE finished
            break
        msg = "Offset: " + str(i) + "\nNumBytes: 1448\n\n"
        if (sz - i < 1448):
            rem = sz%1448
            msg = "Offset: " + str(i) + "\nNumBytes: " + str(rem) + "\n\n"
        sock.sendto(msg.encode('utf-8'), (UDP_IP, UDP_PORT))
    #Now burst_sz number of msgs have been sent
    recvd_cnt = 0
    rec_time = 0
    
    time.sleep(3*time_taken_avg)
    st = time.time()
    for i in range(burst_size):
        try:
            data, addr = sock.recvfrom(4096)  # Buffer size is 4096 bytes
            #need to parse datas now
            data_decoded = data.decode()
            # print("i = ", i)
            start = 0
            i1 = -1
            i2 = -1
            for ind in range(0, len(data_decoded)):
                if i1 == -1 and data_decoded[ind] == " ":
                    i1 = ind+1
                if i2 == -1 and data_decoded[ind] == '\n':
                    i2 = ind
                if(data_decoded[ind] + data_decoded[ind+1] == "\n\n"):
                    start = ind+2
                    break
            o = data_decoded[i1:i2]
            o = int(o)
            rec_offset_arr.append(o)
            rec_offset_time.append((time.time() - starting_time)*1000)
            # print(i1, i2, start)
            # print(o)
            # print(data_decoded)
            squished = data_decoded[start-10:start-2]
            if squished == "Squished":
                print("Squished!!  burst_size = ", burst_size)
                print("Squished!!  burst_size = ", burst_size)
                print("Squished!!  burst_size = ", burst_size)
                print("Squished!!  burst_size = ", burst_size)
                l.append(("SQUISHED", total_lost))
                burst_size = max(burst_size//2, 1)
                squish_arr.append(1)
                squish_time.append(time.time() - starting_time)
                # exit()
                # t_sleep+=0.005
            # print(squished)
            hmap[o] = data_decoded[start:]
            recvd_cnt+=1
            et = time.time() - st
            if(recvd_cnt == 1):
                new_est = et
                if new_est > 0.001:
                    new_rtt = (1- ewma_alpha)*time_taken_avg + ewma_alpha * new_est
                    print(new_rtt)
        except socket.timeout as e:
            continue
            print("Timeout error\n")
        except socket.error as e:
            print("Error occurred while receiving data:", e)
    l.append((recvd_cnt, burst_size))
    burst_arr.append(burst_size)
    time_arr.append((time.time() - starting_time)*1000)
    # if recvd_cnt/burst_size > 0.95:
    #     safe_sz = max(safe_sz, burst_size)
    #     print("Safe_sz = ", safe_sz)
    print(recvd_cnt)
    total_lost+=(burst_size - rec_cnt)
    if recvd_cnt/burst_size >= 0.85:
        burst_size=min(11, burst_size+1)
        # if burst_size > 6:
        #     time_taken_avg = max(time_taken_avg-0.001, 0.003)
        # time_taken_avg/=1.01
        # t_sleep = max(0.008, t_sleep-0.002)
    elif recvd_cnt/burst_size < 0.85:
        burst_size = max(burst_size//2, 1)
        # time_taken_avg*=1.01
    sock.settimeout(max(0.7*burst_size*time_taken_avg,0.037))
    print(burst_size, recvd_cnt/burst_size)
print(len(l), l)
ans = ""

for i in range(0, int(sz), 1448):
    ans+=hmap[i]
#     print(hmap[i])
#     print("NEXT")
# print("ANS = ", ans)
ans = ans[0:-1] + "\n"
with open('output.txt', 'w') as file:
    # Write the string to the file
    file.write(ans)
# print(sz, len(ans))
print("RTT = ", time_taken_avg)
print()
msg_final = "Submit: 2021CS10098@pokemon\nMD5: "
md5_hash = hashlib.md5(ans.encode()).digest()
md5_hex = ''.join('%02x' % byte for byte in md5_hash)

ans=msg_final+md5_hex+"\n\n"
print(ans)
# print(sz)
sock.sendto(ans.encode('utf-8'), (UDP_IP, UDP_PORT))
while True:
    time.sleep(time_taken_avg)
    try:
        data_final, addr = sock.recvfrom(4096)
        if data_final.decode()[:6] == "Result":
            break
        # print("Received data:", data_final)
    except socket.timeout as e:
        continue
    except Exception as e:
        continue
print(data_final.decode())

# plt.figure(figsize=(10, 6))
# plt.scatter(time_arr, burst_arr,label='Send Requests 1', marker='o', color='b')
# # plt.scatter(burst_arr, label='Receive Requests 1', marker='x', color='peachpuff')
# # plt.scatter(*zip(*send_times_2), label='Send Requests 2', marker='o', color='r')
# # plt.scatter(*zip(*receive_times_2), label='Receive Requests 2', marker='x', color='lightcoral')
# plt.title('Tracing Packets')
# plt.xlabel('Time (milliseconds)')
# plt.ylabel('Offset')
# plt.legend()
# plt.grid(True)
#   # Set x-axis limit to 2500 milliseconds
# plt.show()

# arr_x=[0]*len(time_arr)
# plt.figure(figsize=(10, 6))
# plt.plot(time_arr, burst_arr, label='Burst Size', marker='o', linestyle='-', color='orange',markersize=3, linewidth=0.6)
# plt.plot(time_arr, arr_x, label='0 Burst Size', marker='o', linestyle='-', color='b',markersize=3, linewidth=0.6)

# # plt.plot(receive_times, receive_offsets, label='Receive Requests', marker='x', linestyle='-', color='r')

# plt.title('Burst Size vs Time')
# plt.xlabel('Time (milliseconds)')
# plt.ylabel('Burst Size')
# plt.legend()
# plt.savefig("burst_size.png")
# plt.show()

# plt.figure(figsize=(10, 6))
# plt.scatter(offset_time,offset_arr, label='Send Requests 1', marker='o', color='b',s=7)
# plt.scatter(rec_offset_time,rec_offset_arr, label='Receive Requests 1', marker='x', color='peachpuff',s=13)
# # plt.scatter(rec_offset_time, label='Send Requests 2', marker='o', color='r')
# # plt.scatter(rec_offset_arr, label='Receive Requests 2', marker='x', color='lightcoral')
# plt.title('Tracing Packets')
# plt.xlabel('Time (milliseconds)')
# plt.ylabel('Offset')
# plt.legend()
# plt.grid(True)
# plt.show()
# # plt.xlim(0, 360)  # Set x-axis limit to 2500 milliseconds
# plt.savefig("offset.png")

