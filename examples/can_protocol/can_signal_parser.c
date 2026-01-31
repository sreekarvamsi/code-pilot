/**
 * CAN Protocol Implementation Example
 * Demonstrates automotive CAN message handling
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// CAN message structure
typedef struct {
    uint32_t id;              // CAN identifier
    uint8_t  dlc;             // Data length code (0-8)
    uint8_t  data[8];         // Payload data
    bool     extended_id;     // Standard (11-bit) or Extended (29-bit) ID
    bool     rtr;             // Remote transmission request
} Can_Message_t;

// CAN signal definition
typedef struct {
    uint16_t start_bit;       // Starting bit position
    uint8_t  length;          // Signal length in bits
    float    factor;          // Scaling factor
    float    offset;          // Offset value
    float    min_value;       // Minimum physical value
    float    max_value;       // Maximum physical value
} Can_Signal_t;

/**
 * Extract signal value from CAN message
 * Handles Intel (little-endian) and Motorola (big-endian) byte order
 */
uint64_t Can_ExtractSignal(const Can_Message_t* msg, uint16_t start_bit, uint8_t length, bool motorola)
{
    uint64_t raw_value = 0;
    
    if (motorola) {
        // Motorola byte order (MSB first)
        uint8_t start_byte = start_bit / 8;
        uint8_t start_bit_in_byte = start_bit % 8;
        
        for (uint8_t i = 0; i < length; i++) {
            uint16_t bit_pos = start_bit - i;
            uint8_t byte_idx = bit_pos / 8;
            uint8_t bit_idx = 7 - (bit_pos % 8);
            
            if ((msg->data[byte_idx] >> bit_idx) & 0x01) {
                raw_value |= (1ULL << (length - 1 - i));
            }
        }
    } else {
        // Intel byte order (LSB first)
        for (uint8_t i = 0; i < length; i++) {
            uint16_t bit_pos = start_bit + i;
            uint8_t byte_idx = bit_pos / 8;
            uint8_t bit_idx = bit_pos % 8;
            
            if ((msg->data[byte_idx] >> bit_idx) & 0x01) {
                raw_value |= (1ULL << i);
            }
        }
    }
    
    return raw_value;
}

/**
 * Insert signal value into CAN message
 */
void Can_InsertSignal(Can_Message_t* msg, uint16_t start_bit, uint8_t length, uint64_t value, bool motorola)
{
    if (motorola) {
        // Motorola byte order
        for (uint8_t i = 0; i < length; i++) {
            uint16_t bit_pos = start_bit - i;
            uint8_t byte_idx = bit_pos / 8;
            uint8_t bit_idx = 7 - (bit_pos % 8);
            
            if ((value >> (length - 1 - i)) & 0x01) {
                msg->data[byte_idx] |= (1 << bit_idx);
            } else {
                msg->data[byte_idx] &= ~(1 << bit_idx);
            }
        }
    } else {
        // Intel byte order
        for (uint8_t i = 0; i < length; i++) {
            uint16_t bit_pos = start_bit + i;
            uint8_t byte_idx = bit_pos / 8;
            uint8_t bit_idx = bit_pos % 8;
            
            if ((value >> i) & 0x01) {
                msg->data[byte_idx] |= (1 << bit_idx);
            } else {
                msg->data[byte_idx] &= ~(1 << bit_idx);
            }
        }
    }
}

/**
 * Convert raw signal value to physical value
 */
float Can_SignalToPhysical(uint64_t raw_value, const Can_Signal_t* signal, bool is_signed)
{
    float physical_value;
    
    if (is_signed) {
        // Handle signed values (two's complement)
        int64_t signed_value = (int64_t)raw_value;
        if (raw_value & (1ULL << (signal->length - 1))) {
            // Negative value - extend sign bit
            signed_value |= (~0ULL << signal->length);
        }
        physical_value = (float)signed_value * signal->factor + signal->offset;
    } else {
        physical_value = (float)raw_value * signal->factor + signal->offset;
    }
    
    // Range check
    if (physical_value < signal->min_value) {
        physical_value = signal->min_value;
    } else if (physical_value > signal->max_value) {
        physical_value = signal->max_value;
    }
    
    return physical_value;
}

/**
 * Example: Parse vehicle speed from CAN message
 * Message ID: 0x123, Speed signal at bit 0, length 16 bits
 * Factor: 0.01, Offset: 0, Range: 0-300 km/h
 */
float Can_ParseVehicleSpeed(const Can_Message_t* msg)
{
    Can_Signal_t speed_signal = {
        .start_bit = 0,
        .length = 16,
        .factor = 0.01f,
        .offset = 0.0f,
        .min_value = 0.0f,
        .max_value = 300.0f
    };
    
    // Extract raw value
    uint64_t raw_speed = Can_ExtractSignal(msg, speed_signal.start_bit, 
                                           speed_signal.length, false);
    
    // Convert to physical value
    float vehicle_speed = Can_SignalToPhysical(raw_speed, &speed_signal, false);
    
    return vehicle_speed;
}

/**
 * Example: Create CAN message for engine RPM
 * Message ID: 0x234, RPM signal at bit 16, length 16 bits
 * Factor: 0.25, Offset: 0, Range: 0-8000 RPM
 */
void Can_CreateEngineRpmMessage(Can_Message_t* msg, uint16_t rpm)
{
    // Initialize message
    memset(msg, 0, sizeof(Can_Message_t));
    msg->id = 0x234;
    msg->dlc = 8;
    msg->extended_id = false;
    msg->rtr = false;
    
    // Convert physical value to raw value
    uint64_t raw_rpm = (uint64_t)(rpm / 0.25f);
    
    // Range check (0-8000 RPM)
    if (rpm > 8000) {
        raw_rpm = 32000;  // 8000 / 0.25
    }
    
    // Insert signal into message
    Can_InsertSignal(msg, 16, 16, raw_rpm, false);
}

/**
 * CAN message validation
 * Checks for valid DLC, ID range, etc.
 */
bool Can_ValidateMessage(const Can_Message_t* msg)
{
    // Check DLC
    if (msg->dlc > 8) {
        return false;
    }
    
    // Check ID range
    if (msg->extended_id) {
        if (msg->id > 0x1FFFFFFF) {  // 29-bit max
            return false;
        }
    } else {
        if (msg->id > 0x7FF) {  // 11-bit max
            return false;
        }
    }
    
    return true;
}

/**
 * Example usage
 */
void Can_Example_Usage(void)
{
    Can_Message_t rx_msg, tx_msg;
    
    // Receive and parse vehicle speed
    // Assume rx_msg is filled by CAN driver
    float speed = Can_ParseVehicleSpeed(&rx_msg);
    
    // Create and transmit engine RPM message
    Can_CreateEngineRpmMessage(&tx_msg, 2500);
    if (Can_ValidateMessage(&tx_msg)) {
        // Transmit via CAN driver
        // CanIf_Transmit(tx_msg);
    }
}
