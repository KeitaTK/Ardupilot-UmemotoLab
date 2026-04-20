#pragma once
// MESSAGE TAKI_POS_MOTIVE PACKING

#define MAVLINK_MSG_ID_TAKI_POS_MOTIVE 196


typedef struct __mavlink_taki_pos_motive_t {
 float x_coord; /*<  X coordinate*/
 float y_coord; /*<  Y coordinate*/
 float z_coord; /*<  Z coordinate*/
} mavlink_taki_pos_motive_t;

#define MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN 12
#define MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN 12
#define MAVLINK_MSG_ID_196_LEN 12
#define MAVLINK_MSG_ID_196_MIN_LEN 12

#define MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC 20
#define MAVLINK_MSG_ID_196_CRC 20



#if MAVLINK_COMMAND_24BIT
#define MAVLINK_MESSAGE_INFO_TAKI_POS_MOTIVE { \
    196, \
    "TAKI_POS_MOTIVE", \
    3, \
    {  { "x_coord", NULL, MAVLINK_TYPE_FLOAT, 0, 0, offsetof(mavlink_taki_pos_motive_t, x_coord) }, \
         { "y_coord", NULL, MAVLINK_TYPE_FLOAT, 0, 4, offsetof(mavlink_taki_pos_motive_t, y_coord) }, \
         { "z_coord", NULL, MAVLINK_TYPE_FLOAT, 0, 8, offsetof(mavlink_taki_pos_motive_t, z_coord) }, \
         } \
}
#else
#define MAVLINK_MESSAGE_INFO_TAKI_POS_MOTIVE { \
    "TAKI_POS_MOTIVE", \
    3, \
    {  { "x_coord", NULL, MAVLINK_TYPE_FLOAT, 0, 0, offsetof(mavlink_taki_pos_motive_t, x_coord) }, \
         { "y_coord", NULL, MAVLINK_TYPE_FLOAT, 0, 4, offsetof(mavlink_taki_pos_motive_t, y_coord) }, \
         { "z_coord", NULL, MAVLINK_TYPE_FLOAT, 0, 8, offsetof(mavlink_taki_pos_motive_t, z_coord) }, \
         } \
}
#endif

/**
 * @brief Pack a taki_pos_motive message
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 *
 * @param x_coord  X coordinate
 * @param y_coord  Y coordinate
 * @param z_coord  Z coordinate
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_taki_pos_motive_pack(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg,
                               float x_coord, float y_coord, float z_coord)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN];
    _mav_put_float(buf, 0, x_coord);
    _mav_put_float(buf, 4, y_coord);
    _mav_put_float(buf, 8, z_coord);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#else
    mavlink_taki_pos_motive_t packet;
    packet.x_coord = x_coord;
    packet.y_coord = y_coord;
    packet.z_coord = z_coord;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_TAKI_POS_MOTIVE;
    return mavlink_finalize_message(msg, system_id, component_id, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
}

/**
 * @brief Pack a taki_pos_motive message
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param status MAVLink status structure
 * @param msg The MAVLink message to compress the data into
 *
 * @param x_coord  X coordinate
 * @param y_coord  Y coordinate
 * @param z_coord  Z coordinate
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_taki_pos_motive_pack_status(uint8_t system_id, uint8_t component_id, mavlink_status_t *_status, mavlink_message_t* msg,
                               float x_coord, float y_coord, float z_coord)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN];
    _mav_put_float(buf, 0, x_coord);
    _mav_put_float(buf, 4, y_coord);
    _mav_put_float(buf, 8, z_coord);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#else
    mavlink_taki_pos_motive_t packet;
    packet.x_coord = x_coord;
    packet.y_coord = y_coord;
    packet.z_coord = z_coord;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_TAKI_POS_MOTIVE;
#if MAVLINK_CRC_EXTRA
    return mavlink_finalize_message_buffer(msg, system_id, component_id, _status, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
#else
    return mavlink_finalize_message_buffer(msg, system_id, component_id, _status, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#endif
}

/**
 * @brief Pack a taki_pos_motive message on a channel
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param x_coord  X coordinate
 * @param y_coord  Y coordinate
 * @param z_coord  Z coordinate
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_taki_pos_motive_pack_chan(uint8_t system_id, uint8_t component_id, uint8_t chan,
                               mavlink_message_t* msg,
                                   float x_coord,float y_coord,float z_coord)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN];
    _mav_put_float(buf, 0, x_coord);
    _mav_put_float(buf, 4, y_coord);
    _mav_put_float(buf, 8, z_coord);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#else
    mavlink_taki_pos_motive_t packet;
    packet.x_coord = x_coord;
    packet.y_coord = y_coord;
    packet.z_coord = z_coord;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_TAKI_POS_MOTIVE;
    return mavlink_finalize_message_chan(msg, system_id, component_id, chan, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
}

/**
 * @brief Encode a taki_pos_motive struct
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 * @param taki_pos_motive C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_taki_pos_motive_encode(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg, const mavlink_taki_pos_motive_t* taki_pos_motive)
{
    return mavlink_msg_taki_pos_motive_pack(system_id, component_id, msg, taki_pos_motive->x_coord, taki_pos_motive->y_coord, taki_pos_motive->z_coord);
}

/**
 * @brief Encode a taki_pos_motive struct on a channel
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param taki_pos_motive C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_taki_pos_motive_encode_chan(uint8_t system_id, uint8_t component_id, uint8_t chan, mavlink_message_t* msg, const mavlink_taki_pos_motive_t* taki_pos_motive)
{
    return mavlink_msg_taki_pos_motive_pack_chan(system_id, component_id, chan, msg, taki_pos_motive->x_coord, taki_pos_motive->y_coord, taki_pos_motive->z_coord);
}

/**
 * @brief Encode a taki_pos_motive struct with provided status structure
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param status MAVLink status structure
 * @param msg The MAVLink message to compress the data into
 * @param taki_pos_motive C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_taki_pos_motive_encode_status(uint8_t system_id, uint8_t component_id, mavlink_status_t* _status, mavlink_message_t* msg, const mavlink_taki_pos_motive_t* taki_pos_motive)
{
    return mavlink_msg_taki_pos_motive_pack_status(system_id, component_id, _status, msg,  taki_pos_motive->x_coord, taki_pos_motive->y_coord, taki_pos_motive->z_coord);
}

/**
 * @brief Send a taki_pos_motive message
 * @param chan MAVLink channel to send the message
 *
 * @param x_coord  X coordinate
 * @param y_coord  Y coordinate
 * @param z_coord  Z coordinate
 */
#ifdef MAVLINK_USE_CONVENIENCE_FUNCTIONS

static inline void mavlink_msg_taki_pos_motive_send(mavlink_channel_t chan, float x_coord, float y_coord, float z_coord)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN];
    _mav_put_float(buf, 0, x_coord);
    _mav_put_float(buf, 4, y_coord);
    _mav_put_float(buf, 8, z_coord);

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_POS_MOTIVE, buf, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
#else
    mavlink_taki_pos_motive_t packet;
    packet.x_coord = x_coord;
    packet.y_coord = y_coord;
    packet.z_coord = z_coord;

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_POS_MOTIVE, (const char *)&packet, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
#endif
}

/**
 * @brief Send a taki_pos_motive message
 * @param chan MAVLink channel to send the message
 * @param struct The MAVLink struct to serialize
 */
static inline void mavlink_msg_taki_pos_motive_send_struct(mavlink_channel_t chan, const mavlink_taki_pos_motive_t* taki_pos_motive)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    mavlink_msg_taki_pos_motive_send(chan, taki_pos_motive->x_coord, taki_pos_motive->y_coord, taki_pos_motive->z_coord);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_POS_MOTIVE, (const char *)taki_pos_motive, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
#endif
}

#if MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN <= MAVLINK_MAX_PAYLOAD_LEN
/*
  This variant of _send() can be used to save stack space by re-using
  memory from the receive buffer.  The caller provides a
  mavlink_message_t which is the size of a full mavlink message. This
  is usually the receive buffer for the channel, and allows a reply to an
  incoming message with minimum stack space usage.
 */
static inline void mavlink_msg_taki_pos_motive_send_buf(mavlink_message_t *msgbuf, mavlink_channel_t chan,  float x_coord, float y_coord, float z_coord)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char *buf = (char *)msgbuf;
    _mav_put_float(buf, 0, x_coord);
    _mav_put_float(buf, 4, y_coord);
    _mav_put_float(buf, 8, z_coord);

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_POS_MOTIVE, buf, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
#else
    mavlink_taki_pos_motive_t *packet = (mavlink_taki_pos_motive_t *)msgbuf;
    packet->x_coord = x_coord;
    packet->y_coord = y_coord;
    packet->z_coord = z_coord;

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_TAKI_POS_MOTIVE, (const char *)packet, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_MIN_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_CRC);
#endif
}
#endif

#endif

// MESSAGE TAKI_POS_MOTIVE UNPACKING


/**
 * @brief Get field x_coord from taki_pos_motive message
 *
 * @return  X coordinate
 */
static inline float mavlink_msg_taki_pos_motive_get_x_coord(const mavlink_message_t* msg)
{
    return _MAV_RETURN_float(msg,  0);
}

/**
 * @brief Get field y_coord from taki_pos_motive message
 *
 * @return  Y coordinate
 */
static inline float mavlink_msg_taki_pos_motive_get_y_coord(const mavlink_message_t* msg)
{
    return _MAV_RETURN_float(msg,  4);
}

/**
 * @brief Get field z_coord from taki_pos_motive message
 *
 * @return  Z coordinate
 */
static inline float mavlink_msg_taki_pos_motive_get_z_coord(const mavlink_message_t* msg)
{
    return _MAV_RETURN_float(msg,  8);
}

/**
 * @brief Decode a taki_pos_motive message into a struct
 *
 * @param msg The message to decode
 * @param taki_pos_motive C-struct to decode the message contents into
 */
static inline void mavlink_msg_taki_pos_motive_decode(const mavlink_message_t* msg, mavlink_taki_pos_motive_t* taki_pos_motive)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    taki_pos_motive->x_coord = mavlink_msg_taki_pos_motive_get_x_coord(msg);
    taki_pos_motive->y_coord = mavlink_msg_taki_pos_motive_get_y_coord(msg);
    taki_pos_motive->z_coord = mavlink_msg_taki_pos_motive_get_z_coord(msg);
#else
        uint8_t len = msg->len < MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN? msg->len : MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN;
        memset(taki_pos_motive, 0, MAVLINK_MSG_ID_TAKI_POS_MOTIVE_LEN);
    memcpy(taki_pos_motive, _MAV_PAYLOAD(msg), len);
#endif
}
