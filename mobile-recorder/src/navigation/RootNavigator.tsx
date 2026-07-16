import React from 'react';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import {TouchableOpacity, Text, StyleSheet} from 'react-native';
import {NavigationContainer, DarkTheme} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {HomeScreen} from '../screens/HomeScreen';
import {RecordingDetailScreen} from '../screens/RecordingDetailScreen';
import {SettingsScreen} from '../screens/SettingsScreen';

export type RootStackParamList = {
  Home: undefined;
  RecordingDetail: {id: string};
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const headerStyles = StyleSheet.create({
  settingsLink: {color: '#2f6fed', fontSize: 16},
});

function SettingsHeaderLink({
  navigation,
}: {
  navigation: NativeStackScreenProps<RootStackParamList, 'Home'>['navigation'];
}) {
  return (
    <TouchableOpacity onPress={() => navigation.navigate('Settings')}>
      <Text style={headerStyles.settingsLink}>Settings</Text>
    </TouchableOpacity>
  );
}

export function RootNavigator() {
  return (
    <NavigationContainer theme={DarkTheme}>
      <Stack.Navigator>
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={({navigation}) => ({
            title: 'Recordings',
            headerRight: () => <SettingsHeaderLink navigation={navigation} />,
          })}
        />
        <Stack.Screen
          name="RecordingDetail"
          component={RecordingDetailScreen}
          options={{title: 'Recording'}}
        />
        <Stack.Screen
          name="Settings"
          component={SettingsScreen}
          options={{title: 'Settings'}}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
