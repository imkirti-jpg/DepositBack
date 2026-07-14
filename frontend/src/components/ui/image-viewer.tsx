import React from 'react';
import {
  Modal,
  View,
  Text,
  Image,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Dimensions,
  StyleSheet,
} from 'react-native';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

type ImageViewerProps = {
  visible: boolean;
  onClose: () => void;
  imageUrl: string | null;
  displayName: string;
  category: string;
  uploadedAt: string;
};

export function ImageViewer({
  visible,
  onClose,
  imageUrl,
  displayName,
  category,
  uploadedAt,
}: ImageViewerProps) {
  if (!imageUrl) return null;

  const formattedDate = new Date(uploadedAt).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  const categoryName = category.replace('_', ' ').toUpperCase();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.container}>
        {/* Header Overlay */}
        <View style={styles.header}>
          <View>
            <Text style={styles.categoryText}>{categoryName}</Text>
            <Text style={styles.titleText}>{displayName}</Text>
            <Text style={styles.dateText}>Uploaded on {formattedDate}</Text>
          </View>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        {/* Zoomable Image ScrollView */}
        <ScrollView
          contentContainerStyle={styles.imageContainer}
          maximumZoomScale={3}
          minimumZoomScale={1}
          showsHorizontalScrollIndicator={false}
          showsVerticalScrollIndicator={false}
        >
          <Image
            source={{ uri: imageUrl }}
            style={styles.image}
            resizeMode="contain"
          />
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.95)', // Glassmorphic dark slate overlay
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
    zIndex: 10,
  },
  categoryText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#38bdf8', // Sleek blue highlight
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  titleText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  dateText: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeButtonText: {
    fontSize: 18,
    color: '#ffffff',
    fontWeight: 'bold',
  },
  imageContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  image: {
    width: screenWidth,
    height: screenHeight - 120,
  },
});
