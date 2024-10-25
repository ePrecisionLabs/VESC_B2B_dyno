from pyvesc import VESC
import math
import time


# Adjust here the name of the COM port for each motor and the log file name
motor_dut_port = 'COM4'
motor_absorber_port = 'COM5'
log_file_name = 'dut_log.txt'


# Adjust here the stator current and rpm arrays to test
current_array = [
    1, 2, 5, 10, 15, 20
] # Stator current in A
rpm_array = [
    100, 200, 300, 400, 700, 1000, 2000, 3000
] # RPM


# Other test parameters
test_point_nb_captures = 10 # Number of measurements per test point
test_point_time_btwn_measurements = 0.1 # seconds between measurements
test_point_settling_time_s = 0.5 # seconds to settle at operating point before capturing
ramp_settling_time_s = 0.1 # seconds to settle between each points of a ramp
max_rpm_ramp_step = 500
max_current_ramp_step = 5
max_rpm_error = 10
max_current_error = 1


# Helper functions
def do_rpm_ramp(motor, start_rpm, end_rpm):
    rpm = start_rpm
    nb_steps = math.ceil((end_rpm-start_rpm)/max_rpm_ramp_step)
    for _ in range(nb_steps):
        rpm = rpm + (end_rpm-start_rpm)/nb_steps
        motor.set_rpm(int(rpm))
        time.sleep(ramp_settling_time_s)

def do_current_ramp(motor, start_current, end_current):
    current = start_current
    nb_steps = math.ceil((end_current-start_current)/max_current_ramp_step)
    for _ in range(nb_steps):
        current = current + (end_current-start_current)/nb_steps
        motor.set_current(current*1000) # Set current in mA
        time.sleep(ramp_settling_time_s)

def log_measurements_to_file(measurements):
    log_file.write(f'\
            {measurements.time_ms},
            {measurements.rpm},
            {measurements.duty_cycle_now},
            {measurements.v_in},
            {measurements.avg_motor_current},
            {measurements.avg_input_current},
            {measurements.temp_fet},
            {measurements.temp_motor}\n')


# Test script execution below
last_rpm = 0
last_current = 0
isFaulted = False

with open(log_file_name, "w") as log_file:
    log_file.write(f'time_ms, rpm, duty_cycle, v_in, avg_motor_current, avg_input_current, temp_fet, temp_motor\n')
    with VESC(serial_port=motor_dut_port) as motor_dut:
        with VESC(serial_port=motor_absorber_port) as motor_absorber:

            log_file.write(f"DUT Firmware: {motor_dut.get_firmware_version()}")
            log_file.write(f"Absorber Firmware: {motor_absorber.get_firmware_version()}")

            for rpm in rpm_array:
                do_rpm_ramp(motor_absorber, last_rpm, rpm)
                for current in current_array:
                    do_current_ramp(motor_dut, last_current, current)
                    time.sleep(test_point_settling_time_s)

                    wrong_rpm = abs(rpm - motor_absorber.get_rpm()) > max_rpm_error
                    wrong_current = abs(current - motor_dut.get_motor_current()) > max_current_error
                    if wrong_rpm or wrong_current:
                        log_file.write(f'Unable to reach operating point. RPM error={wrong_rpm}, Current error={wrong_current}\n')
                        isFaulted = True
                        break

                    for _ in range(test_point_nb_captures):
                        measurements_dut = motor_dut.get_measurements()
                        log_measurements_to_file(measurements_dut)
                        if measurements_dut.mc_fault_code > 0:
                            log_file.write(f'DUT faulted with code {measurements_dut.mc_fault_code}\n')
                            isFaulted = True
                            break

                        measurements_abs = motor_absorber.get_measurements()
                        if measurements_abs.mc_fault_code != b'\x00':
                            log_file.write(f'Absorber faulted with code {measurements_abs.mc_fault_code}\n')
                            isFaulted = True
                            break

                        time.sleep(test_point_time_btwn_measurements)

                    last_current = current
                    if isFaulted:
                        break

                do_current_ramp(motor_dut, last_current, 0)
                last_rpm = rpm
                if isFaulted:
                    break

            do_rpm_ramp(motor_absorber, last_rpm, 0)

