#pragma once
// MESSAGE TAKI_CUSTOME1 PACKING

#define MAVLINK_MSG_ID_TAKI_CUSTOME1 190


typedef struct __mavlink_taki_custome1_t {
 uint32_t test_counter; /*<  Test counter value*/
 uint16_t taki_system_id; /*<  System ID*/
 uint16_t taki_component_id; /*<  Component ID*/
} mavlink_taki_custome1_t;

#define MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN 8
#define MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN 8
#define MAVLINK_MSG_ID_190_LEN 8
#define MAVLINK_MSG_ID_190_MIN_LEN 8

#define MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC 177
#define MAVLINK_MSG_ID_190_CRC 177



#if MAVLINK_COMMAND_24BIT
#define MAVLINK_MESSAGE_INFO_TAKI_CUSTOME1 { \
    190, \
    "TAKI_CUSTOME1", \
    3, \
    {  { "test_counter", NULL, MAVLINK_TYPE_UINT32_T, 0, 0, offsetof(mavlink_taki_custome1_t, test_counter) }, \
         { "taki_system_id", NULL, MAVLINK_TYPE_UINT16_T, 0, 4, offsetof(mavlink_taki_custome1_t, taki_system_id) }, \
         { "taki_component_id", NULL, MAVLINK_TYPE_UINT16_T, 0, 6, offsetof(mavlink_taki_custome1_t, taki_component_id) }, \
         } \
}
#else
#define MAVLINK_MESSAGE_INFO_TAKI_CUSTOME1 { \
    "TAKI_CUSTOME1", \
    3, \
    {  { "test_counter", NULL, MAVLINK_TYPE_UINT32_T, 0, 0, offsetof(mavlink_taki_custome1_t, test_counter) }, \
         { "taki_system_id", NULL, MAVLINK_TYPE_UINT16_T, 0, 4, offsetof(mavlink_taki_custome1_t, taki_system_id) }, \
         { "taki_component_id", NULL, MAVLINK_TYPE_UINT16_T, 0, 6, offsetof(mavlink_taki_custome1_t, taki_component_id) }, \
         } \
}
#endif

/**
 * @brief Pack a taki_custome1 message
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 *
 * @param test_counter  Test counter value
 * @param taki_system_id  System ID
 * @param taki_component_id  Component ID
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_taki_custome1_pack(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg,
                               uint32_t test_counter, uint16_t taki_system_id, uint16_t taki_component_id)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN];
    _mav_put_uint32_t(buf, 0, test_counter);
    _mav_put_uint16_t(buf, 4, taki_system_id);
    _mav_put_uint16_t(buf, 6, taki_component_id);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#else
    mavlink_taki_custome1_t packet;
    packet.test_counter = test_counter;
    packet.taki_system_id = taki_system_id;
    packet.taki_component_id = taki_component_id;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_TAKI_CUSTOME1;
    return mavlink_finalize_message(msg, system_id, component_id, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
}

/**
 * @brief Pack a taki_custome1 message
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param status MAVLink status structure
 * @param msg The MAVLink message to compress the data into
 *
 * @param test_counter  Test counter value
 * @param taki_system_id  System ID
 * @param taki_component_id  Component ID
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_taki_custome1_pack_status(uint8_t system_id, uint8_t component_id, mavlink_status_t *_status, mavlink_message_t* msg,
                               uint32_t test_counter, uint16_t taki_system_id, uint16_t taki_component_id)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN];
    _mav_put_uint32_t(buf, 0, test_counter);
    _mav_put_uint16_t(buf, 4, taki_system_id);
    _mav_put_uint16_t(buf, 6, taki_component_id);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#else
    mavlink_taki_custome1_t packet;
    packet.test_counter = test_counter;
    packet.taki_system_id = taki_system_id;
    packet.taki_component_id = taki_component_id;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_TAKI_CUSTOME1;
#if MAVLINK_CRC_EXTRA
    return mavlink_finalize_message_buffer(msg, system_id, component_id, _status, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
#else
    return mavlink_finalize_message_buffer(msg, system_id, component_id, _status, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#endif
}

/**
 * @brief Pack a taki_custome1 message on a channel
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param test_counter  Test counter value
 * @param taki_system_id  System ID
 * @param taki_component_id  Component ID
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_taki_custome1_pack_chan(uint8_t system_id, uint8_t component_id, uint8_t chan,
                               mavlink_message_t* msg,
                                   uint32_t test_counter,uint16_t taki_system_id,uint16_t taki_component_id)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN];
    _mav_put_uint32_t(buf, 0, test_counter);
    _mav_put_uint16_t(buf, 4, taki_system_id);
    _mav_put_uint16_t(buf, 6, taki_component_id);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#else
    mavlink_taki_custome1_t packet;
    packet.test_counter = test_counter;
    packet.taki_system_id = taki_system_id;
    packet.taki_component_id = taki_component_id;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_TAKI_CUSTOME1;
    return mavlink_finalize_message_chan(msg, system_id, component_id, chan, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
}

/**
 * @brief Encode a taki_custome1 struct
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 * @param taki_custome1 C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_taki_custome1_encode(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg, const mavlink_taki_custome1_t* taki_custome1)
{
    return mavlink_msg_taki_custome1_pack(system_id, component_id, msg, taki_custome1->test_counter, taki_custome1->taki_system_id, taki_custome1->taki_component_id);
}

/**
 * @brief Encode a taki_custome1 struct on a channel
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param taki_custome1 C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_taki_custome1_encode_chan(uint8_t system_id, uint8_t component_id, uint8_t chan, mavlink_message_t* msg, const mavlink_taki_custome1_t* taki_custome1)
{
    return mavlink_msg_taki_custome1_pack_chan(system_id, component_id, chan, msg, taki_custome1->test_counter, taki_custome1->taki_system_id, taki_custome1->taki_component_id);
}

/**
 * @brief Encode a taki_custome1 struct with provided status structure
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param status MAVLink status structure
 * @param msg The MAVLink message to compress the data into
 * @param taki_custome1 C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_taki_custome1_encode_status(uint8_t system_id, uint8_t component_id, mavlink_status_t* _status, mavlink_message_t* msg, const mavlink_taki_custome1_t* taki_custome1)
{
    return mavlink_msg_taki_custome1_pack_status(system_id, component_id, _status, msg,  taki_custome1->test_counter, taki_custome1->taki_system_id, taki_custome1->taki_component_id);
}

/**
 * @brief Send a taki_custome1 message
 * @param chan MAVLink channel to send the message
 *
 * @param test_counter  Test counter value
 * @param taki_system_id  System ID
 * @param taki_component_id  Component ID
 */
#ifdef MAVLINK_USE_CONVENIENCE_FUNCTIONS

static inline void mavlink_msg_taki_custome1_send(mavlink_channel_t chan, uint32_t test_counter, uint16_t taki_system_id, uint16_t taki_component_id)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN];
    _mav_put_uint32_t(buf, 0, test_counter);
    _mav_put_uint16_t(buf, 4, taki_system_id);
    _mav_put_uint16_t(buf, 6, taki_component_id);

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_CUSTOME1, buf, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
#else
    mavlink_taki_custome1_t packet;
    packet.test_counter = test_counter;
    packet.taki_system_id = taki_system_id;
    packet.taki_component_id = taki_component_id;

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_CUSTOME1, (const char *)&packet, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
#endif
}

/**
 * @brief Send a taki_custome1 message
 * @param chan MAVLink channel to send the message
 * @param struct The MAVLink struct to serialize
 */
static inline void mavlink_msg_taki_custome1_send_struct(mavlink_channel_t chan, const mavlink_taki_custome1_t* taki_custome1)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    mavlink_msg_taki_custome1_send(chan, taki_custome1->test_counter, taki_custome1->taki_system_id, taki_custome1->taki_component_id);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_CUSTOME1, (const char *)taki_custome1, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
#endif
}

#if MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN <= MAVLINK_MAX_PAYLOAD_LEN
/*
  This variant of _send() can be used to save stack space by re-using
  memory from the receive buffer.  The caller provides a
  mavlink_message_t which is the size of a full mavlink message. This
  is usually the receive buffer for the channel, and allows a reply to an
  incoming message with minimum stack space usage.
 */
static inline void mavlink_msg_taki_custome1_send_buf(mavlink_message_t *msgbuf, mavlink_channel_t chan,  uint32_t test_counter, uint16_t taki_system_id, uint16_t taki_component_id)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char *buf = (char *)msgbuf;
    _mav_put_uint32_t(buf, 0, test_counter);
    _mav_put_uint16_t(buf, 4, taki_system_id);
    _mav_put_uint16_t(buf, 6, taki_component_id);

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_CUSTOME1, buf, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
#else
    mavlink_taki_custome1_t *packet = (mavlink_taki_custome1_t *)msgbuf;
    packet->test_counter = test_counter;
    packet->taki_system_id = taki_system_id;
    packet->taki_component_id = taki_component_id;

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_CUSTOME1, (const char *)packet, MAVLINK_MSG_ID_TAKI_CUSTOME1_MIN_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN, MAVLINK_MSG_ID_TAKI_CUSTOME1_CRC);
#endif
}
#endif

#endif

// MESSAGE TAKI_CUSTOME1 UNPACKING


/**
 * @brief Get field test_counter from taki_custome1 message
 *
 * @return  Test counter value
 */
static inline uint32_t mavlink_msg_taki_custome1_get_test_counter(const mavlink_message_t* msg)
{
    return _MAV_RETURN_uint32_t(msg,  0);
}

/**
 * @brief Get field taki_system_id from taki_custome1 message
 *
 * @return  System ID
 */
static inline uint16_t mavlink_msg_taki_custome1_get_taki_system_id(const mavlink_message_t* msg)
{
    return _MAV_RETURN_uint16_t(msg,  4);
}

/**
 * @brief Get field taki_component_id from taki_custome1 message
 *
 * @return  Component ID
 */
static inline uint16_t mavlink_msg_taki_custome1_get_taki_component_id(const mavlink_message_t* msg)
{
    return _MAV_RETURN_uint16_t(msg,  6);
}

/**
 * @brief Decode a taki_custome1 message into a struct
 *
 * @param msg The message to decode
 * @param taki_custome1 C-struct to decode the message contents into
 */
static inline void mavlink_msg_taki_custome1_decode(const mavlink_message_t* msg, mavlink_taki_custome1_t* taki_custome1)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    taki_custome1->test_counter = mavlink_msg_taki_custome1_get_test_counter(msg);
    taki_custome1->taki_system_id = mavlink_msg_taki_custome1_get_taki_system_id(msg);
    taki_custome1->taki_component_id = mavlink_msg_taki_custome1_get_taki_component_id(msg);
#else
        uint8_t len = msg->len < MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN? msg->len : MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN;
        memset(taki_custome1, 0, MAVLINK_MSG_ID_TAKI_CUSTOME1_LEN);
    memcpy(taki_custome1, _MAV_PAYLOAD(msg), len);
#endif
}
